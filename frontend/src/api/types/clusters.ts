/**
 * Clusters types
 */

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
  ip_range_names: string[]
  vxlan_range_names: string[]
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
