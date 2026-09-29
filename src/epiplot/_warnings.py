"""Warnings shown by epiplot."""


class EpiplotWarning(UserWarning):
    """A nudge about good practice, such as an unlabelled date type.

    To hide only epiplot's warnings, and keep warnings from other libraries::

        import warnings
        from epiplot import EpiplotWarning

        warnings.simplefilter("ignore", EpiplotWarning)
    """
