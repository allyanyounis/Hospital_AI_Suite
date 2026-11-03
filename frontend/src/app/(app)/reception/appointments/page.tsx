import { redirect } from "next/navigation";

/** The appointments board moved to /appointments when booking became a hospital-wide module. */
export default function Page() {
  redirect("/appointments");
}
