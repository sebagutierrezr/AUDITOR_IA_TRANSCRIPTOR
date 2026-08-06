import re
from pathlib import Path

import numpy as np

from app.models.conversation import Conversation


class DiarizationService:
    TARGET_RATE = 16000
    MIN_SEGMENT_SECONDS = 0.70

    def diarize(
        self,
        conversation: Conversation,
        audio_path: Path,
        speaker_one_label: str,
        speaker_two_label: str,
        first_speaker_is_one: bool,
        progress_callback=None,
    ) -> Conversation:
        if len(conversation.segments) < 2:
            return conversation

        if progress_callback:
            progress_callback(
                91,
                "PREPARANDO IDENTIFICACIÓN DE VOCES...",
            )

        samples = self._decode_mono(audio_path)
        features = []
        valid_indices = []

        for index, segment in enumerate(
            conversation.segments
        ):
            start = max(
                0,
                int(segment.start * self.TARGET_RATE),
            )
            end = min(
                len(samples),
                int(segment.end * self.TARGET_RATE),
            )

            if (
                end - start
                < int(
                    self.TARGET_RATE
                    * self.MIN_SEGMENT_SECONDS
                )
            ):
                continue

            feature = self._features(
                samples[start:end]
            )

            if feature is None:
                continue

            features.append(feature)
            valid_indices.append(index)

        if len(features) < 2:
            return conversation

        matrix = np.vstack(features)
        matrix = self._standardize(matrix)
        labels = self._two_means(matrix)
        labels = self._smooth(labels)

        first_cluster = labels[0]

        if first_speaker_is_one:
            mapping = {
                first_cluster: speaker_one_label,
                1 - first_cluster: speaker_two_label,
            }
        else:
            mapping = {
                first_cluster: speaker_two_label,
                1 - first_cluster: speaker_one_label,
            }

        assignments = {
            segment_index: mapping[label]
            for segment_index, label in zip(
                valid_indices,
                labels,
            )
        }

        known = sorted(assignments)
        previous = None

        for index, segment in enumerate(
            conversation.segments
        ):
            speaker = assignments.get(index)

            if speaker is None:
                speaker = previous or self._nearest(
                    index,
                    known,
                    assignments,
                    speaker_one_label,
                )

            previous = speaker
            segment.speaker = speaker
            segment.text = self._apply_label(
                segment.text,
                speaker,
            )

        if progress_callback:
            progress_callback(
                99,
                "AGENTE Y CLIENTE IDENTIFICADOS",
            )

        return conversation

    def _decode_mono(
        self,
        audio_path: Path,
    ) -> np.ndarray:
        import av

        chunks = []

        with av.open(str(audio_path)) as container:
            stream = next(
                (
                    item
                    for item in container.streams
                    if item.type == "audio"
                ),
                None,
            )

            if stream is None:
                raise RuntimeError(
                    "EL ARCHIVO NO CONTIENE AUDIO."
                )

            resampler = av.AudioResampler(
                format="s16",
                layout="mono",
                rate=self.TARGET_RATE,
            )

            for frame in container.decode(stream):
                converted = resampler.resample(frame)

                if converted is None:
                    continue

                frames = (
                    converted
                    if isinstance(converted, list)
                    else [converted]
                )

                for item in frames:
                    chunks.append(
                        item.to_ndarray()
                        .reshape(-1)
                        .astype(np.float32)
                    )

        if not chunks:
            raise RuntimeError(
                "NO FUE POSIBLE LEER EL AUDIO."
            )

        samples = np.concatenate(chunks)
        peak = float(
            np.max(np.abs(samples))
        )

        if peak > 0:
            samples /= peak

        return samples

    def _features(
        self,
        samples: np.ndarray,
    ) -> np.ndarray | None:
        samples = samples.astype(
            np.float32,
            copy=False,
        )
        samples -= float(np.mean(samples))

        energy = float(
            np.sqrt(
                np.mean(samples * samples)
                + 1e-10
            )
        )

        if energy < 0.003:
            return None

        frame_size = 400
        hop = 160

        if len(samples) < frame_size:
            return None

        frame_count = (
            1
            + (
                len(samples)
                - frame_size
            )
            // hop
        )
        indices = (
            np.arange(frame_size)[None, :]
            + hop
            * np.arange(frame_count)[:, None]
        )
        frames = samples[indices]
        frames *= np.hanning(
            frame_size
        ).astype(np.float32)

        spectrum = (
            np.abs(
                np.fft.rfft(
                    frames,
                    n=512,
                )
            )
            + 1e-8
        )
        power = spectrum * spectrum
        freqs = np.fft.rfftfreq(
            512,
            d=1.0 / self.TARGET_RATE,
        )
        total_power = (
            np.sum(power, axis=1)
            + 1e-8
        )
        centroid = (
            np.sum(
                power * freqs[None, :],
                axis=1,
            )
            / total_power
        )
        zero_crossing = np.mean(
            np.abs(
                np.diff(
                    np.signbit(frames),
                    axis=1,
                )
            ),
            axis=1,
        )

        edges = np.linspace(
            80,
            7600,
            13,
        )
        bands = []

        for low, high in zip(
            edges[:-1],
            edges[1:],
        ):
            mask = (
                (freqs >= low)
                & (freqs < high)
            )

            if np.any(mask):
                values = np.log(
                    np.mean(
                        power[:, mask],
                        axis=1,
                    )
                    + 1e-8
                )
                bands.extend(
                    [
                        float(np.mean(values)),
                        float(np.std(values)),
                    ]
                )

        return np.asarray(
            [
                energy,
                float(np.mean(centroid)),
                float(np.std(centroid)),
                float(np.mean(zero_crossing)),
                float(np.std(zero_crossing)),
                *bands,
            ],
            dtype=np.float32,
        )

    @staticmethod
    def _standardize(
        matrix: np.ndarray,
    ) -> np.ndarray:
        mean = np.mean(
            matrix,
            axis=0,
            keepdims=True,
        )
        std = np.std(
            matrix,
            axis=0,
            keepdims=True,
        )
        std[std < 1e-6] = 1.0
        return (matrix - mean) / std

    @staticmethod
    def _two_means(
        matrix: np.ndarray,
    ) -> list[int]:
        first = 0
        second = int(
            np.argmax(
                np.sum(
                    (matrix - matrix[first]) ** 2,
                    axis=1,
                )
            )
        )
        centers = np.vstack(
            [
                matrix[first],
                matrix[second],
            ]
        )
        labels = np.zeros(
            len(matrix),
            dtype=np.int32,
        )

        for _ in range(20):
            distances = np.stack(
                [
                    np.sum(
                        (matrix - centers[0]) ** 2,
                        axis=1,
                    ),
                    np.sum(
                        (matrix - centers[1]) ** 2,
                        axis=1,
                    ),
                ],
                axis=1,
            )
            updated = np.argmin(
                distances,
                axis=1,
            ).astype(np.int32)

            if np.array_equal(
                labels,
                updated,
            ):
                break

            labels = updated

            for cluster in (0, 1):
                members = matrix[
                    labels == cluster
                ]

                if len(members):
                    centers[cluster] = np.mean(
                        members,
                        axis=0,
                    )

        if len(set(labels.tolist())) < 2:
            labels = np.asarray(
                [
                    index % 2
                    for index in range(
                        len(matrix)
                    )
                ],
                dtype=np.int32,
            )

        return labels.tolist()

    @staticmethod
    def _smooth(
        labels: list[int],
    ) -> list[int]:
        output = labels[:]

        for index in range(
            1,
            len(output) - 1,
        ):
            if (
                output[index - 1]
                == output[index + 1]
                != output[index]
            ):
                output[index] = output[index - 1]

        return output

    @staticmethod
    def _nearest(
        index: int,
        known: list[int],
        assignments: dict[int, str],
        fallback: str,
    ) -> str:
        if not known:
            return fallback

        nearest = min(
            known,
            key=lambda item: abs(
                item - index
            ),
        )
        return assignments[nearest]

    @staticmethod
    def _apply_label(
        text: str,
        speaker: str,
    ) -> str:
        timestamp = re.match(
            r"^(\[[^\]]+\]\s*)(.*)$",
            text,
            flags=re.DOTALL,
        )

        if timestamp:
            prefix, body = timestamp.groups()
            body = re.sub(
                r"^\s*[^:\n]{1,40}:\s*",
                "",
                body,
                count=1,
            )
            return (
                f"{prefix}{speaker}: "
                f"{body.strip()}"
            )

        clean = re.sub(
            r"^\s*[^:\n]{1,40}:\s*",
            "",
            text,
            count=1,
        )
        return (
            f"{speaker}: "
            f"{clean.strip()}"
        )
