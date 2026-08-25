from __future__ import annotations

import importlib
import inspect
import os
import sys


def patch_speechbrain_lazy_import() -> bool:
    try:
        from speechbrain.utils import importutils as iu
    except Exception:
        return False

    if getattr(iu.LazyModule, "_auditor_ia_windows_patch", False):
        return True

    def ensure_module(self, stacklevel: int):
        importer_frame = None

        try:
            importer_frame = inspect.getframeinfo(
                sys._getframe(stacklevel + 1)
            )
        except (AttributeError, ValueError):
            importer_frame = None

        if (
            importer_frame is not None
            and os.path.basename(importer_frame.filename) == "inspect.py"
        ):
            raise AttributeError()

        if self.lazy_module is None:
            try:
                if self.package is None:
                    self.lazy_module = importlib.import_module(self.target)
                else:
                    self.lazy_module = importlib.import_module(
                        f".{self.target}",
                        self.package,
                    )
            except Exception as exc:
                raise ImportError(
                    f"Lazy import of {self!r} failed"
                ) from exc

        return self.lazy_module

    iu.LazyModule.ensure_module = ensure_module
    iu.LazyModule._auditor_ia_windows_patch = True
    return True
