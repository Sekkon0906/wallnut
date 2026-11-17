export interface CampusPost {
  id: string
  author_id: string
  author: string
  author_profile_visible: boolean
  body: string
  has_photo: boolean
  mine: boolean
  created_at: string
  updated_at: string | null
  hidden: boolean
  moderation_reason: string | null
  reported: boolean
}

export interface CampusPostReport {
  post: CampusPost
  report_count: number
  latest_reason: string
  latest_at: string
}

export const postPageSize = 20

export const postDate = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'America/Bogota',
})
