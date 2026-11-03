import { PatientChartView } from "@/features/clinical";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PatientChartView patientId={Number(id)} />;
}
