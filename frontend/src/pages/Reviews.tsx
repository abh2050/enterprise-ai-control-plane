import { useQuery } from "@tanstack/react-query";
import { get } from "../api";
import { EmptyState, Loading, PageHeader, QueryError } from "../components/ui";

export default function Reviews() {
  const pending = useQuery({ queryKey: ["reviews"], queryFn: () => get<unknown[]>("/reviews/pending") });
  return (
    <>
      <PageHeader
        title="Reviews"
        summary="Pending gate approvals and routed cases. The person who submitted an item can never approve it."
      />
      {pending.error ? (
        <QueryError error={pending.error} />
      ) : !pending.data ? (
        <Loading />
      ) : (
        <EmptyState
          title="Nothing is waiting for review"
          missing="Gate requests and cases routed to review."
          action="Gate approvals arrive with the lifecycle in M4; routed cases arrive with shadow replay in M5."
        />
      )}
    </>
  );
}
