/**
 * AI voice receptionist feature: the voice agent (a booking channel) and its call costs. Appointments themselves
 * live in the appointments feature, shared by every channel.
 * Public API of the module: import from "@/features/reception", never from its internal files.
 */

export { AgentView } from "./views/AgentView";
export { MonitoringView } from "./views/MonitoringView";
