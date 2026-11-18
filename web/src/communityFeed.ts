import type { WorkshopCall } from './client'
import type { CampusPost } from './campusPosts'
import type { EventCard } from './campusEvents'

export type FeedKind = 'post' | 'event' | 'call'
export interface FeedTarget { kind: FeedKind; id: string }

interface FeedRecord extends FeedTarget {
  published_at: string
  institutional: boolean
}

export type FeedEntry =
  | FeedRecord & { kind: 'post'; content: CampusPost }
  | FeedRecord & { kind: 'event'; content: EventCard }
  | FeedRecord & { kind: 'call'; content: WorkshopCall }

export interface FeedPage { items: FeedEntry[]; next_cursor: string | null }
