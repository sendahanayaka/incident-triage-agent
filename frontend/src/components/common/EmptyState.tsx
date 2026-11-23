import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  action,
}) => {
  return (
    <div className="state-container" data-testid="empty-state">
      <div className="state-icon">
        {icon || <Inbox size={40} />}
      </div>
      <h3 className="state-title">{title}</h3>
      <p className="state-description">{description}</p>
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
};
