"""Shared benchmark helpers present in this evidence-qualified source slice.

The PF01/A1 source package deliberately vendors only ``task_instances`` from
the larger research repository.  Importing this package must therefore not
eagerly import modules that are absent from the frozen slice.
"""

__all__: list[str] = []
