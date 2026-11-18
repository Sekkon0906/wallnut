export type EventCategory = 'workshop' | 'tournament' | 'campus'
export type TournamentFormat = 'individual' | 'doubles'
export const eventCategories = { workshop: 'Taller', tournament: 'Torneo', campus: 'Encuentro' }

export interface EventCard {
  id: string
  title: string
  description: string
  category: EventCategory
  starts_at: string
  location: string
  capacity: number
  organizer: string
  institutional: boolean
  cancelled: boolean
  organizer_id: string
  organizer_profile_visible: boolean
  mine: boolean
  upcoming: boolean
  attendees: number
  enrolled: boolean
  registration_open: boolean
  tournament_format: TournamentFormat
}
