// Valid Cedar policy for CLI testing
permit(
    principal == User::"alice",
    action == Action::"read",
    resource == Document::"doc1"
);

// Another policy
permit(
    principal in Group::"admins",
    action,
    resource
);