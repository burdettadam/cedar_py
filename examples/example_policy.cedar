// Example Cedar Policy

// Basic policy allowing alice to read doc123
permit(
  principal == User::"alice",
  action == Action::"read",
  resource == Document::"doc123"
);

// Context-based policy allowing bob to write doc456 only during business hours
permit(
  principal == User::"bob",
  action == Action::"write",
  resource == Document::"doc456"
)
when { 
  context.time.hour >= 9 && context.time.hour < 17 
};

// Group-based policy allowing any admin to delete any document
permit(
  principal in AdminGroup::"admins",
  action == Action::"delete",
  resource like Document::*
);
