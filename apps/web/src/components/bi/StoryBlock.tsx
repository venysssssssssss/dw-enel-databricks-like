type Props = { lead: string; children: React.ReactNode };

export function StoryBlock({ lead, children }: Props) {
  return (
    <section className="story-block">
      <div className="lead">{lead}</div>
      <div className="body">{children}</div>
    </section>
  );
}
