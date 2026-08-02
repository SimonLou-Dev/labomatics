/**
 * Clusters types
 */

export interface RangeRef {
  id: string
  name: string
}

export interface ClusterDTO {
  id: string
  name: string
  url: string
  default_storage: string
  sdn_zone: string
  wan_bridge: string
  is_active: boolean
  is_default_for_new_cohorts: boolean
  has_credential: boolean
  token_id: string | null
  ip_ranges: RangeRef[]
  vxlan_ranges: RangeRef[]
}

export interface ClusterCreateDTO {
  name: string
  url: string
  default_storage: string
  sdn_zone: string
  wan_bridge?: string
  is_active?: boolean
  is_default_for_new_cohorts?: boolean
}

export interface ClusterUpdateDTO {
  name?: string
  url?: string
  default_storage?: string
  sdn_zone?: string
  wan_bridge?: string
  is_active?: boolean
  is_default_for_new_cohorts?: boolean
}

export interface ClusterCredentialWriteDTO {
  token_id: string
  token_secret: string
}
