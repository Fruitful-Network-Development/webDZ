"""Interface stubs for muniment access contract data."""


class MunimentAccessContract:
    """Describe muniment access request/response shapes.

    Intended inputs:
        - muniment identifiers (document IDs, types)
        - subject identifiers requesting access
        - optional access context (tenant, environment, purpose)

    Intended outputs:
        - access decision (allow/deny)
        - authorized muniment references
        - optional reason codes or audit metadata

    TODO:
        - Define muniment identifier fields.
        - Define subject identifier fields.
        - Define audit metadata and reason codes.
    """

    def evaluate_access(self, subject, muniment_ids, context=None):
        """Evaluate access for muniment resources.

        Args:
            subject: Subject identifier input (TODO: specify fields).
            muniment_ids: Muniment identifiers (TODO: define type).
            context: Optional request context (TODO: specify fields).

        Returns:
            Muniment access decision payload (TODO: define fields).
        """
        raise NotImplementedError
