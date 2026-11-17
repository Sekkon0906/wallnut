export type Role = 'student' | 'staff' | 'faculty' | 'admin'

export interface Account {
  id: string
  email: string
  display_name: string
  role: Role
}

export interface Course {
  id: string
  code: string
  title: string
  term: string
  section: string
  faculty: string
  enrolled: boolean
}

export type ApplicationStatus = 'pending' | 'approved' | 'not_selected'

export interface WorkshopCall {
  id: string
  course_id: string
  title: string
  description: string
  created_at: string
  course: string
  faculty: string
  open: boolean
  can_manage: boolean
  can_schedule: boolean
  my_application: ApplicationStatus | null
}

export interface Application {
  id: string
  display_name: string
  proposal: string
  evidence_url: string | null
  status: ApplicationStatus
}

export interface Workshop {
  id: string
  call_id: string
  title: string
  course: string
  facilitator_name: string
  starts_at: string
  ends_at: string
  location: string
  capacity: number
  enrolled_count: number
  enrolled: boolean
  attended: boolean
  can_manage: boolean
  can_cancel: boolean
  can_issue_code: boolean
  is_facilitator: boolean
  cancelled_at: string | null
  schedule_revision: number
  schedule_change: 'rescheduled' | 'cancelled' | null
  schedule_notice: string | null
  previous_starts_at: string | null
}

export interface AttendanceCode {
  code: string
  qr_value: string
  expires_at: string
}

export interface Attendance {
  checked_in_at: string
  already_recorded: boolean
}

export interface WorkshopEvidence {
  id: string
  student_id: string
  display_name: string
  reflection: string
  status: 'submitted' | 'returned' | 'approved'
  comment: string | null
  submitted_at: string
  photo_content_type: string
  points_awarded: number
  goal_verified: boolean
  reward_points: number
}

export interface WorkshopEconomy {
  attendee_points: number
  facilitator_points: number
  goal_description: string | null
  goal_coins: number | null
  coin_cost: number | null
  conversion_points: number | null
  points_scope: 'course_only' | 'accepted_courses'
}

export interface FacultyBudget {
  faculty_id: string
  display_name: string
  available_points: number
}

export interface WalletMovement {
  id: string
  kind: 'evidence_reward' | 'goal_coins' | 'coin_conversion' | 'grade_redemption'
    | 'ardy_purchase' | 'ardy_nut' | 'coin_sent' | 'coin_received'
  points: number
  coins: number
  course: string
  workshop: string | null
  created_at: string
}

export interface WalletConversion {
  workshop_id: string
  evidence_id: string
  workshop: string
  course: string
  goal: string
  coin_cost: number
  points: number
  converted: boolean
}

export interface Wallet {
  coins: number
  points: number
  reserved_points: number
  movements: WalletMovement[]
  conversions: WalletConversion[]
}

export type GradeCourse = Pick<Course, 'id' | 'code' | 'title' | 'term' | 'section'>

export interface GradeRuleInput {
  assessment: string
  points_per_step: number
  step_milli: number
  max_bonus_milli: number
  minimum_grade_milli: number | null
  accepted_course_ids: string[]
}

export interface GradeRule extends GradeRuleInput {
  locked: boolean
}

export interface GradeRequest {
  id: string
  student_id: string
  display_name: string
  assessment: string
  points: number
  boost_milli: number
  grade_before_milli: number
  grade_after_milli: number
  status: 'pending' | 'approved' | 'rejected'
  reason: string | null
  created_at: string
}

export interface GradeRosterEntry {
  student_id: string
  display_name: string
  email: string
  base_grade_milli: number | null
  locked: boolean
}

export interface GradeStudent {
  base_grade_milli: number | null
  simulated_grade_milli: number | null
  eligible_points: number
  remaining_bonus_milli: number
}

export interface GradeRedemption {
  rule: GradeRule | null
  roster: GradeRosterEntry[]
  requests: GradeRequest[]
  student: GradeStudent | null
}

export class RequestError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
    this.name = 'RequestError'
  }
}

export const localDemo = import.meta.env.VITE_DEMO === 'true'
export const googleClientId = String(import.meta.env.VITE_GOOGLE_CLIENT_ID ?? '')
const apiOrigin = String(import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

export function errorText(error: unknown) {
  if (error instanceof RequestError) return error.message
  return 'No pudimos conectar con Wallnut. Intenta nuevamente.'
}

type RequestOptions = {
  token?: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: object | FormData
}

async function request<T>(path: string, options: RequestOptions, accept: string,
                          read: (response: Response) => Promise<T>): Promise<T> {
  const headers: Record<string, string> = { Accept: accept }
  if (options.token) headers.Authorization = `Bearer ${options.token}`
  let body: BodyInit | undefined
  if (options.data instanceof FormData) {
    body = options.data
  } else if (options.data) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.data)
  }

  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), body instanceof FormData ? 60000 : 15000)
  try {
    const response = await fetch(`${apiOrigin}/v1${path}`, {
      method: options.method ?? 'GET',
      headers,
      body,
      cache: 'no-store',
      signal: controller.signal,
    })
    if (!response.ok) {
      const result = await response.json().catch(() => null)
      const detail = typeof result?.detail === 'string'
        ? result.detail
        : 'Revisa los datos y vuelve a intentarlo.'
      throw new RequestError(detail, response.status)
    }
    return await read(response)
  } finally {
    window.clearTimeout(timeout)
  }
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return request(path, options, 'application/json', async (response) => {
    if (response.status === 204) return undefined as T
    return await response.json() as T
  })
}

export async function apiPhoto(path: string, token: string): Promise<Blob> {
  return request(path, { token }, 'image/jpeg', (response) => response.blob())
}
