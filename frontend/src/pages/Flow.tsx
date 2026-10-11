import { EmptyState, PageHeader, Section } from "../components/ui";

export default function Flow() {
  return (
    <>
      <PageHeader
        title="Flow"
        summary="How applications move between lifecycle stages over time."
      />
      <Section title="Stage transitions">
        <EmptyState
          title="No transition history yet"
          missing="Lifecycle events over a period."
          action="The Sankey chart, weekly in and out bars, and median stage durations arrive in M6, built from registry events."
        />
      </Section>
    </>
  );
}
