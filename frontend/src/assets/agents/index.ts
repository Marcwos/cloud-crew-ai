import type { AgentId } from '../../features/crew-office/domain/types'
import leslie from './leslie.png'
import alan from './alan.png'
import edgar from './edgar.png'
import hedy from './hedy.png'
import grace from './grace.png'
import vint from './vint.png'

/** Pixel-art sprite (transparent PNG) for each agent. */
export const AGENT_SPRITE: Record<AgentId, string> = {
  leslie,
  alan,
  edgar,
  hedy,
  grace,
  vint,
}
