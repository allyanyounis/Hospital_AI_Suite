import { CaseView } from "@/features/theatre";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <CaseView caseId={Number(id)} />;
}
