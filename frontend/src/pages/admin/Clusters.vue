<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-3xl font-bold">Clusters Proxmox</h1>
      <div class="flex gap-3">
        <Button
          label="Importer YAML"
          icon="pi pi-upload"
          severity="secondary"
          @click="showImportDialog = true"
        />
        <Button
          label="Créer"
          icon="pi pi-plus"
          @click="openCreateDialog"
        />
      </div>
    </div>

    <DataTable
      paginator
      :rows="pageSize"
      :rowsPerPageOptions="[5, 10, 20, 50]"
      :value="clusters"
      dataKey="id"
      :totalRecords="totalRecords"
      :loading="loading"
      @page="onPageChange"
    >
      <template #empty>Aucun cluster trouvé</template>
      <Column field="name" header="Nom" style="width: 15%">
        <template #body="{ data }">
          <span class="font-semibold">{{ data.name }}</span>
        </template>
      </Column>
      <Column field="url" header="URL" style="width: 15%">
        <template #body="{ data }">
          <span class="font-mono text-sm"><a :href="data.url" target="_blanck">Console proxmox</a></span>
        </template>
      </Column>
      <Column field="default_storage" header="Stockage" style="width: 10%">
        <template #body="{ data }">
          <span class="font-semibold">{{ data.default_storage }}</span>
        </template>
      </Column>
      <Column field="sdn_zone" header="Zone SDN" style="width: 12%">
        <template #body="{ data }">
          <span class="font-semibold">{{ data.sdn_zone }}</span>
        </template>
      </Column>
      <Column field="wan_bridge" header="Bridge WAN" style="width: 10%">
        <template #body="{ data }">
          <span class="font-semibold">{{ data.wan_bridge }}</span>
        </template>
      </Column>
      <Column field="has_credential" header="Credential" style="width: 10%">
        <template #body="{ data }">
          <Badge
            :value="data.has_credential ? 'Configuré' : 'Absent'"
            :severity="data.has_credential ? 'success' : 'warning'"
          />
        </template>
      </Column>
      <Column field="ip_ranges" header="Plages IP" style="width: 12%">
        <template #body="{ data }">
          <div v-if="data.ip_ranges.length > 0" class="flex flex-wrap gap-1">
            <Chip
              v-for="range in data.ip_ranges"
              :key="range.id"
              :label="range.name"
              class="text-xs cursor-pointer"
              @click="() => goToVxlanDetails(range.id)"
            />
          </div>
          <span v-else class="text-surface-400">—</span>
        </template>
      </Column>
      <Column field="vxlan_ranges" header="Plages VXLAN" style="width: 12%">
        <template #body="{ data }">
          <div v-if="data.vxlan_ranges.length > 0" class="flex flex-wrap gap-1">
            <Chip
              v-for="range in data.vxlan_ranges"
              :key="range.id"
              :label="range.name"
              class="text-xs cursor-pointer"
               @click="() => goToWanDetails(range.id)"
            />
          </div>
          <span v-else class="text-surface-400">—</span>
        </template>
      </Column>
      <Column field="is_default_for_new_cohorts" header="Défaut" style="width: 8%">
        <template #body="{ data }">
          <Badge
            v-if="data.is_default_for_new_cohorts"
            value="★"
            severity="info"
            class="text-lg"
          />
          <span v-else class="text-surface-400">—</span>
        </template>
      </Column>
      <Column field="actions" header="Actions" style="width: 18%" frozen align-frozen="right">
        <template #body="{ data }">
          <div class="flex gap-2">
            <Button
              icon="pi pi-pencil"
              severity="secondary"
              size="small"
              v-tooltip="'Éditer'"
              @click="openEditDialog(data)"
            />
            <Button
              icon="pi pi-shield"
              severity="info"
              size="small"
              v-tooltip="'Credential'"
              @click="openCredentialDialog(data)"
            />
            <Button
              icon="pi pi-check"
              severity="warning"
              size="small"
              :loading="testingConnection === data.id"
              v-tooltip="'Tester la connexion'"
              @click="testConnection(data)"
            />
            <Button
              icon="pi pi-link"
              severity="warning"
              size="small"
              v-tooltip="'Gérer plages'"
              @click="openRangesDialog(data)"
            />
            <Button
              icon="pi pi-star"
              :severity="data.is_default_for_new_cohorts ? 'success' : 'secondary'"
              size="small"
              v-tooltip="data.is_default_for_new_cohorts ? 'Défaut' : 'Définir défaut'"
              @click="setDefaultCluster(data)"
            />
            <Button
              icon="pi pi-trash"
              severity="danger"
              size="small"
              v-tooltip="'Supprimer'"
              @click="confirmDeleteCluster(data)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <!-- Create/Edit Dialog -->
    <Dialog
      v-model:visible="showFormDialog"
      :header="editingCluster ? 'Éditer le cluster' : 'Créer un cluster'"
      modal
      :style="{ width: '100vw', maxWidth: '600px' }"
    >
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-2">Nom</label>
          <InputText
            v-model="formData.name"
            class="w-full"
            placeholder="ex: cluster-1"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">URL</label>
          <InputText
            v-model="formData.url"
            class="w-full"
            placeholder="ex: https://proxmox.example.com:8006"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Stockage</label>
          <InputText
            v-model="formData.default_storage"
            class="w-full"
            placeholder="ex: local-lvm"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Zone SDN</label>
          <InputText
            v-model="formData.sdn_zone"
            class="w-full"
            placeholder="ex: vxlan-zone"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Bridge WAN</label>
          <InputText
            v-model="formData.wan_bridge"
            class="w-full"
            placeholder="ex: vmbr0"
          />
        </div>
      </div>

      <template #footer>
        <Button
          label="Annuler"
          severity="secondary"
          @click="showFormDialog = false"
        />
        <Button
          :label="editingCluster ? 'Mettre à jour' : 'Créer'"
          :loading="formLoading"
          @click="saveCluster"
        />
      </template>
    </Dialog>

    <!-- Credential Dialog -->
    <Dialog
      v-model:visible="showCredentialDialog"
      header="Configurer la credential"
      modal
      :style="{ width: '100vw', maxWidth: '500px' }"
    >
      <div class="space-y-4">
        <p class="text-sm text-surface-600">
          Entrez les credentials Proxmox pour {{ credentialCluster?.name }}
        </p>
        <div>
          <label class="block text-sm font-medium mb-2">Token ID</label>
          <InputText
            v-model="credentialData.tokenId"
            class="w-full"
            placeholder="ex: root@pam!token1"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Token Secret</label>
          <Password
            v-model="credentialData.tokenSecret"
            class="w-full"
            placeholder="Token secret"
            :feedback="false"
          />
        </div>
      </div>

      <template #footer>
        <Button
          label="Annuler"
          severity="secondary"
          @click="showCredentialDialog = false"
        />
        <Button
          label="Sauvegarder"
          :loading="formLoading"
          @click="saveCredential"
        />
      </template>
    </Dialog>

    <!-- Ranges Dialog -->
    <Dialog
      v-model:visible="showRangesDialog"
      header="Gérer les plages réseau"
      modal
      :style="{ width: '100vw', maxWidth: '800px' }"
    >
      <div class="space-y-6">
        <!-- IP Ranges -->
        <div>
          <h3 class="text-lg font-semibold mb-3">Plages IP WAN</h3>
          <div class="flex flex-wrap gap-2 mb-3">
            <div
              v-for="ipRange in availableIpRanges"
              :key="ipRange.id"
              class="flex items-center gap-2 bg-surface-700 rounded px-3 py-2"
            >
              <span class="text-sm font-medium">{{ ipRange.name }}</span>
              <Button
                icon="pi pi-arrow-right"
                size="small"
                text
                severity="info"
                v-tooltip="'Consulter'"
                @click="goToWanRangeDetails(ipRange.id)"
              />
              <Button
                v-if="rangesCluster?.ip_ranges.some((r) => r.id === ipRange.id)"
                icon="pi pi-times"
                size="small"
                text
                severity="danger"
                v-tooltip="'Détacher'"
                @click="detachIPRange(ipRange.id)"
              />
              <Button
                v-else
                icon="pi pi-plus"
                size="small"
                text
                severity="success"
                v-tooltip="'Attacher'"
                @click="attachIPRange(ipRange.id)"
              />
            </div>
          </div>
        </div>

        <!-- VXLAN Ranges -->
        <div>
          <h3 class="text-lg font-semibold mb-3">Plages VXLAN</h3>
          <div class="flex flex-wrap gap-2 mb-3">
            <div
              v-for="vxlanRange in availableVxlanRanges"
              :key="vxlanRange.id"
              class="flex items-center gap-2 bg-surface-700 rounded px-3 py-2"
            >
              <span class="text-sm font-medium">{{ vxlanRange.name }}</span>
              <Button
                icon="pi pi-arrow-right"
                size="small"
                text
                severity="info"
                v-tooltip="'Consulter'"
                @click="goToNetworkRangeDetails(vxlanRange.id)"
              />
              <Button
                v-if="rangesCluster?.vxlan_ranges.some((r) => r.id === vxlanRange.id)"
                icon="pi pi-times"
                size="small"
                text
                severity="danger"
                v-tooltip="'Détacher'"
                @click="detachVxlanRange(vxlanRange.id)"
              />
              <Button
                v-else
                icon="pi pi-plus"
                size="small"
                text
                severity="success"
                v-tooltip="'Attacher'"
                @click="attachVxlanRange(vxlanRange.id)"
              />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          label="Fermer"
          @click="showRangesDialog = false"
        />
      </template>
    </Dialog>

    <!-- Import Dialog -->
    <Dialog
      v-model:visible="showImportDialog"
      header="Importer configuration YAML"
      modal
      :style="{ width: '100vw', maxWidth: '500px' }"
    >
      <div class="space-y-4">
        <FileUpload
          ref="fileUpload"
          name="file"
          :url="`${apiUrl}/clusters/apply-config`"
          :auto="false"
          :show-upload-button="false"
          :show-cancel-button="false"
          accept=".yaml,.yml"
          @select="onFileSelect"
        />
      </div>

      <template #footer>
        <Button
          label="Annuler"
          severity="secondary"
          @click="showImportDialog = false"
        />
        <Button
          label="Importer"
          :loading="importLoading"
          :disabled="!selectedFile"
          @click="importClusterConfig"
        />
      </template>
    </Dialog>

    <!-- Delete Confirm Dialog (via useConfirm) -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import {
  DataTable,
  Column,
  Dialog,
  Button,
  InputText,
  Password,
  Badge,
  Chip,
  FileUpload,
} from 'primevue'
import type {
  ClusterDTO,
  ClusterCreateDTO,
  IpRangeDTO,
  VxlanRangeDTO,
} from '@/api/types'
import * as clusterApi from '@/api/clusters'
import * as ipRangeApi from '@/api/ipRanges'
import * as vxlanRangeApi from '@/api/vxlanRanges'
import { useRouter } from 'vue-router'

const toast = useToast()
const confirm = useConfirm()
const router = useRouter()

const apiUrl = import.meta.env.VITE_API_URL ?? '/api'

const clusters = ref<ClusterDTO[]>([])
const totalRecords = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)

const showFormDialog = ref(false)
const editingCluster = ref<ClusterDTO | null>(null)
const formLoading = ref(false)
const formData = ref<ClusterCreateDTO>({
  name: '',
  url: '',
  default_storage: '',
  sdn_zone: '',
  wan_bridge: '',
})

const showCredentialDialog = ref(false)
const credentialCluster = ref<ClusterDTO | null>(null)
const credentialData = ref({ tokenId: '', tokenSecret: '' })

const showRangesDialog = ref(false)
const rangesCluster = ref<ClusterDTO | null>(null)
const availableIpRanges = ref<IpRangeDTO[]>([])
const availableVxlanRanges = ref<VxlanRangeDTO[]>([])

const showImportDialog = ref(false)
const selectedFile = ref<File | null>(null)
const importLoading = ref(false)
const fileUpload = ref()

const testingConnection = ref<string | null>(null)

async function fetchClusters(page: number = 1) {
  loading.value = true
  try {
    const response = await clusterApi.listClusters(page, pageSize.value)
    clusters.value = response.items
    totalRecords.value = response.total
    currentPage.value = page
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de charger les clusters',
      life: 3000,
    })
    console.error('Failed to fetch clusters:', error)
  } finally {
    loading.value = false
  }
}

function onPageChange(event: any) {
  const newPage = Math.floor(event.first / event.rows) + 1
  fetchClusters(newPage)
}

function openCreateDialog() {
  editingCluster.value = null
  formData.value = {
    name: '',
    url: '',
    storage: '',
    sdn_zone: '',
    wan_bridge: '',
  }
  showFormDialog.value = true
}

function openEditDialog(cluster: ClusterDTO) {
  editingCluster.value = cluster
  formData.value = {
    name: cluster.name,
    url: cluster.url,
    default_storage: cluster.default_storage,
    sdn_zone: cluster.sdn_zone,
    wan_bridge: cluster.wan_bridge,
  }
  showFormDialog.value = true
}

async function saveCluster() {
  formLoading.value = true
  try {
    if (editingCluster.value) {
      await clusterApi.updateCluster(editingCluster.value.id, formData.value)
      toast.add({
        severity: 'success',
        summary: 'Succès',
        detail: 'Cluster mis à jour',
        life: 3000,
      })
    } else {
      await clusterApi.createCluster(formData.value)
      toast.add({
        severity: 'success',
        summary: 'Succès',
        detail: 'Cluster créé',
        life: 3000,
      })
    }
    showFormDialog.value = false
    await fetchClusters(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de sauvegarder le cluster',
      life: 3000,
    })
    console.error('Failed to save cluster:', error)
  } finally {
    formLoading.value = false
  }
}

function openCredentialDialog(cluster: ClusterDTO) {
  credentialCluster.value = cluster
  credentialData.value = { tokenId: '', tokenSecret: '' }
  showCredentialDialog.value = true
}

async function saveCredential() {
  if (!credentialCluster.value) return
  formLoading.value = true
  try {
    await clusterApi.setClusterCredential(
      credentialCluster.value.id,
      credentialData.value.tokenId,
      credentialData.value.tokenSecret
    )
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Credential configurée',
      life: 3000,
    })
    showCredentialDialog.value = false
    await fetchClusters(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de configurer la credential',
      life: 3000,
    })
    console.error('Failed to set credential:', error)
  } finally {
    formLoading.value = false
  }
}

async function testConnection(cluster: ClusterDTO) {
  testingConnection.value = cluster.id
  try {
    const result = await clusterApi.testClusterConnection(cluster.id)
    if (result.success) {
      toast.add({
        severity: 'success',
        summary: 'Succès',
        detail: result.message,
        life: 3000,
      })
    } else {
      toast.add({
        severity: 'error',
        summary: 'Erreur',
        detail: result.message,
        life: 5000,
      })
    }
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de tester la connexion',
      life: 3000,
    })
    console.error('Failed to test connection:', error)
  } finally {
    testingConnection.value = null
  }
}

function goToWanRangeDetails(rangeId: string) {
  router.push(`/admin/wan/${rangeId}`)
}

function goToNetworkRangeDetails(rangeId: string) {
  router.push(`/admin/networks/${rangeId}`)
}

async function openRangesDialog(cluster: ClusterDTO) {
  rangesCluster.value = cluster
  showRangesDialog.value = true
  loading.value = true
  try {
    const ipRangesRes = await ipRangeApi.listIpRanges(1, 100)
    const vxlanRangesRes = await vxlanRangeApi.listVxlanRanges(1, 100)
    availableIpRanges.value = ipRangesRes.items
    availableVxlanRanges.value = vxlanRangesRes.items
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de charger les plages réseau',
      life: 3000,
    })
    console.error('Failed to fetch ranges:', error)
  } finally {
    loading.value = false
  }
}

async function attachIPRange(ipRangeId: string) {
  if (!rangesCluster.value) return
  try {
    await clusterApi.attachIpRange(rangesCluster.value.id, ipRangeId)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Plage IP attachée',
      life: 3000,
    })
    await fetchClusters(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible d\'attacher la plage IP',
      life: 3000,
    })
    console.error('Failed to attach IP range:', error)
  }
}

async function detachIPRange(ipRangeId: string) {
  if (!rangesCluster.value) return
  try {
    await clusterApi.detachIpRange(rangesCluster.value.id, ipRangeId)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Plage IP détachée',
      life: 3000,
    })
    await fetchClusters(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de détacher la plage IP',
      life: 3000,
    })
    console.error('Failed to detach IP range:', error)
  }
}

async function attachVxlanRange(vxlanRangeId: string) {
  if (!rangesCluster.value) return
  try {
    await clusterApi.attachVxlanRange(rangesCluster.value.id, vxlanRangeId)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Plage VXLAN attachée',
      life: 3000,
    })
    await fetchClusters(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible d\'attacher la plage VXLAN',
      life: 3000,
    })
    console.error('Failed to attach VXLAN range:', error)
  }
}

async function detachVxlanRange(vxlanRangeId: string) {
  if (!rangesCluster.value) return
  try {
    await clusterApi.detachVxlanRange(rangesCluster.value.id, vxlanRangeId)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Plage VXLAN détachée',
      life: 3000,
    })
    await fetchClusters(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de détacher la plage VXLAN',
      life: 3000,
    })
    console.error('Failed to detach VXLAN range:', error)
  }
}

async function setDefaultCluster(cluster: ClusterDTO) {
  try {
    await clusterApi.setDefaultCluster(cluster.id)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Cluster par défaut défini',
      life: 3000,
    })
    await fetchClusters(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de définir le cluster par défaut',
      life: 3000,
    })
    console.error('Failed to set default cluster:', error)
  }
}

function confirmDeleteCluster(cluster: ClusterDTO) {
  confirm.require({
    message: `Êtes-vous sûr de vouloir supprimer le cluster "${cluster.name}" ?`,
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    accept: () => deleteCluster(cluster.id),
  })
}

async function deleteCluster(id: string) {
  try {
    await clusterApi.deleteCluster(id)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Cluster supprimé',
      life: 3000,
    })
    await fetchClusters(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de supprimer le cluster',
      life: 3000,
    })
    console.error('Failed to delete cluster:', error)
  }
}

function onFileSelect(event: any) {
  const file = event.files[0]
  if (file) {
    selectedFile.value = file
  }
}

function goToVxlanDetails(id: string) {
  router.push(`/admin/networks/${id}`)
}

function goToWanDetails(id: string) {
  router.push(`/admin/wan/${id}`)
}

async function importClusterConfig() {
  if (!selectedFile.value) return
  importLoading.value = true
  try {
    await clusterApi.applyClusterConfig(selectedFile.value)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Configuration importée',
      life: 3000,
    })
    showImportDialog.value = false
    selectedFile.value = null
    await fetchClusters(1)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible d\'importer la configuration',
      life: 3000,
    })
    console.error('Failed to import config:', error)
  } finally {
    importLoading.value = false
  }
}

onMounted(() => {
  fetchClusters()
})
</script>
