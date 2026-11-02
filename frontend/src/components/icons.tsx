/**
 * The app's icon set: one place that maps names to lucide-react icons, so every module uses the same style.
 * Default size is 16px; pass className to resize.
 */
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  BookOpen,
  Bot,
  CalendarClock,
  CalendarDays,
  Check,
  CheckCircle2,
  Clock,
  Coffee,
  Copy,
  Eye,
  FileText,
  Headphones,
  LayoutDashboard,
  ListChecks,
  LogOut,
  type LucideIcon,
  Mic,
  Pencil,
  Phone,
  Plus,
  Radio,
  RefreshCw,
  Search,
  Sparkles,
  Stethoscope,
  Sun,
  Tag,
  Upload,
  User,
} from "lucide-react";

type IconProps = { className?: string };

const icon = (Component: LucideIcon) =>
  function Icon({ className }: IconProps) {
    return <Component className={className ?? "h-4 w-4"} aria-hidden />;
  };

export const Icons = {
  Activity: icon(Activity),
  Alert: icon(AlertTriangle),
  ArrowLeft: icon(ArrowLeft),
  ArrowRight: icon(ArrowRight),
  Book: icon(BookOpen),
  Bot: icon(Bot),
  Calendar: icon(CalendarDays),
  CalendarClock: icon(CalendarClock),
  Chart: icon(BarChart3),
  Check: icon(Check),
  CheckCircle: icon(CheckCircle2),
  Clock: icon(Clock),
  Coffee: icon(Coffee),
  Copy: icon(Copy),
  Eye: icon(Eye),
  File: icon(FileText),
  Grid: icon(LayoutDashboard),
  Headphones: icon(Headphones),
  ListCheck: icon(ListChecks),
  Logo: icon(Stethoscope),
  Logout: icon(LogOut),
  Mic: icon(Mic),
  Pencil: icon(Pencil),
  Phone: icon(Phone),
  Plus: icon(Plus),
  Pulse: icon(Activity),
  Radio: icon(Radio),
  Refresh: icon(RefreshCw),
  Search: icon(Search),
  Sparkles: icon(Sparkles),
  Sun: icon(Sun),
  Tag: icon(Tag),
  Upload: icon(Upload),
  User: icon(User),
};

export type IconComponent = (typeof Icons)[keyof typeof Icons];
