<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import 'ol/ol.css'
import Map from 'ol/Map'
import View from 'ol/View'
import TileLayer from 'ol/layer/Tile'
import VectorLayer from 'ol/layer/Vector'
import OSM from 'ol/source/OSM'
import VectorSource from 'ol/source/Vector'
import ClusterSource from 'ol/source/Cluster'
import { fromLonLat, toLonLat } from 'ol/proj'
import Feature from 'ol/Feature'
import Point from 'ol/geom/Point'
import { boundingExtent } from 'ol/extent'
import { Fill, Icon, Stroke, Style, Text } from 'ol/style'
import ScaleLine from 'ol/control/ScaleLine'

const APP_VERSION = '0.3.27'
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const currentRoute = ref(window.location.hash || '#/')

const currentRoutePath = computed(() => {
  const path = currentRoute.value.replace(/^#/, '')
  return path || '/'
})

const isDiagnosticsPage = computed(() => currentRoutePath.value === '/diagnostics')

const mapTarget = ref(null)
let mapInstance = null
let mapMarkerSource = null
let mapClusterSource = null
let mapMarkerLayer = null
let manualGpsSource = null
let manualGpsLayer = null
let mapClickReady = false


const projects = ref([])
const currentProject = ref(null)

const projectForm = ref({
  name: '',
  code: '',
  description: '',
})

const projectMessage = ref('')
const uploadMessage = ref('')

const assets = ref([])
const mapAssets = ref([])
const mapAssetsMessage = ref('尚未加载地图点位。')
const mapAssetsLoading = ref(false)
const assetFilter = ref('all')
const expandedAssetIds = ref(new Set())
const previewAsset = ref(null)
const mapPointGroupAssets = ref([])
const selectedAssetId = ref(null)

const manualGpsAsset = ref(null)
const manualGpsDraft = ref(null)
const manualGpsSaving = ref(false)
const manualGpsMessage = ref('尚未进入补点模式。')

const sidebarOpen = ref(false)
const SIDEBAR_DEFAULT_WIDTH = 340
const SIDEBAR_MIN_WIDTH = 200
const SIDEBAR_MAX_WIDTH = 720
const sidebarWidth = ref(SIDEBAR_DEFAULT_WIDTH)
const sidebarWidthBeforeMaximize = ref(SIDEBAR_DEFAULT_WIDTH)
const sidebarMaximized = ref(false)
const sidebarResizing = ref(false)
let sidebarResizeFrame = null
const activeSidebarTab = ref('project')
const sidebarTabs = [
  { key: 'project', name: '项目' },
  { key: 'photos', name: '照片' },
  { key: 'noGps', name: '无GPS' },
  { key: 'points', name: '点位' },
  { key: 'tasks', name: '任务' },
  { key: 'export', name: '导出' },
]
const mapSearchKeyword = ref('')
const mapUiPanel = ref(null)
const mapUiMessage = ref('')

const basemapOptions = [
  { key: 'standard', name: '标准地图', note: '当前默认 OpenStreetMap 底图' },
  { key: 'work', name: '工程底图', note: '后续版本可接入工程专用底图' },
  { key: 'satellite', name: '影像底图', note: '后续版本可接入卫星影像或天地图影像' },
]
const activeBasemap = ref('standard')
const currentPageUrl = computed(() => window.location.href)

const fileInputRef = ref(null)
const selectedFiles = ref([])
const uploading = ref(false)

const tasks = ref([])
const taskSummary = ref(null)
const taskStatusFilter = ref('all')
const taskScope = ref('current')
const taskMessage = ref('')
const smartPollingRunning = ref(false)
const smartPollingMessage = ref('智能轮询空闲。')
const smartPollingLastRefresh = ref('')
let smartPollingTimer = null
let smartPollingBusy = false

const trackedTaskId = ref(null)
const trackedTask = ref(null)
const trackedTaskMessage = ref('')
const trackedTaskTimer = ref(null)
const trackedTaskPolling = ref(false)

const diagnosticsRunning = ref(false)
const diagnosticsMessage = ref('尚未检测。')
const diagnosticsLastRun = ref('')
const diagnosticsResults = ref([])

const exportRunning = ref(false)

const printMapOptions = ref({
  paperSize: 'A4',
  orientation: 'landscape',
  quality: 'standard',
  range: 'current_project',
  showScale: true,
  showNorth: true,
  showPointNumber: true,
  showTitle: true,
})

const printPhotoLayoutOptions = [
  { value: '1x1', name: '1 × 1（每页 1 张）' },
  { value: '1x2', name: '1 × 2（每页 2 张）' },
  { value: '2x2', name: '2 × 2（每页 4 张）' },
  { value: '3x3', name: '3 × 3（每页 9 张）' },
  { value: '4x4', name: '4 × 4（每页 16 张）' },
  { value: '5x5', name: '5 × 5（每页 25 张）' },
  { value: '6x6', name: '6 × 6（每页 36 张）' },
  { value: '7x7', name: '7 × 7（每页 49 张）' },
  { value: '8x8', name: '8 × 8（每页 64 张）' },
  { value: '9x9', name: '9 × 9（每页 81 张）' },
]

const printPhotoOptions = ref({
  paperSize: 'A4',
  orientation: 'portrait',
  layout: '2x2',
  includeInfo: true,
  includePageNo: true,
})

const printMapPreviewLoading = ref(false)
const printMapPreview = ref({
  open: false,
  imageUrl: '',
  title: '',
  createdAt: '',
  optionsText: '',
  pointCount: 0,
  paperSize: 'A4',
  orientation: 'landscape',
  scaleText: '',
  scaleLabel: '',
  scaleBarWidth: 120,
})

const printPhotoPreview = ref({
  open: false,
  title: '',
  createdAt: '',
  optionsText: '',
  paperSize: 'A4',
  orientation: 'portrait',
  layout: '2x2',
  includeInfo: true,
  includePageNo: true,
  totalCount: 0,
  pages: [],
})

const printPackagePreview = ref({
  open: false,
  title: '',
  createdAt: '',
  mapOptionsText: '',
  photoOptionsText: '',
  totalPhotos: 0,
  gpsPhotos: 0,
  noGpsPhotos: 0,
  mapPoints: 0,
  packageFiles: [],
  nextSteps: [],
})

const printMapPreviewPaperClass = computed(() => {
  return [
    'print-preview-sheet',
    `paper-${printMapPreview.value.paperSize.toLowerCase()}`,
    `paper-${printMapPreview.value.orientation}`,
  ]
})

const printPhotoPreviewPaperClass = computed(() => {
  return [
    'print-photo-preview-sheet',
    `paper-${printPhotoPreview.value.paperSize.toLowerCase()}`,
    `paper-${printPhotoPreview.value.orientation || 'portrait'}`,
    `layout-${printPhotoPreview.value.layout}`,
  ]
})

const printMapOrientationText = computed(() => {
  return printMapOptions.value.orientation === 'landscape' ? '横向' : '纵向'
})

const printMapQualityText = computed(() => {
  if (printMapOptions.value.quality === 'small') return '小体积'
  if (printMapOptions.value.quality === 'high') return '高清'
  return '标准'
})

const printMapRangeText = computed(() => {
  return printMapOptions.value.range === 'current_view' ? '当前地图视野' : '当前项目全部点位'
})

const printMapElementText = computed(() => {
  const extra = []
  if (printMapOptions.value.showTitle) extra.push('标题')
  if (printMapOptions.value.showScale) extra.push('比例尺')
  if (printMapOptions.value.showNorth) extra.push('指北针')
  if (printMapOptions.value.showPointNumber) extra.push('点位编号')
  return extra.join('、') || '无附加元素'
})

const printMapOptionText = computed(() => {
  return `${printMapOptions.value.paperSize} / ${printMapOrientationText.value} / ${printMapQualityText.value} / ${printMapRangeText.value} / 显示：${printMapElementText.value}`
})

const printPhotoOptionText = computed(() => {
  const orientationText = printPhotoOptions.value.orientation === 'landscape' ? '横向' : '纵向'
  const infoText = printPhotoOptions.value.includeInfo ? '含照片信息' : '仅照片'
  const pageText = printPhotoOptions.value.includePageNo ? '含页码' : '无页码'
  return `${printPhotoOptions.value.paperSize} / ${orientationText} / ${printPhotoOptions.value.layout} / ${infoText} / ${pageText}`
})

const currentProjectName = computed(() => {
  return currentProject.value?.name || '尚未选择项目'
})

const currentProjectId = computed(() => {
  return currentProject.value?.id || null
})

const assetStats = computed(() => {
  const total = assets.value.length
  const gps = assets.value.filter((item) => itemHasGps(item)).length
  const noGps = total - gps
  const processed = assets.value.filter((item) => assetProcessed(item)).length
  const pending = total - processed

  return {
    total,
    gps,
    noGps,
    processed,
    pending,
  }
})



const mapPointStats = computed(() => {
  const valid = mapAssets.value.filter((item) => isValidMapAsset(item)).length

  return {
    total: mapAssets.value.length,
    valid,
    invalid: mapAssets.value.length - valid,
  }
})

const sidebarStyle = computed(() => ({
  width: sidebarMaximized.value ? '100vw' : `${sidebarWidth.value}px`,
  maxWidth: sidebarMaximized.value ? '100vw' : 'none',
}))

const rightPanelStyle = computed(() => ({
  left: sidebarOpen.value && !sidebarMaximized.value ? `${sidebarWidth.value}px` : '0px',
}))

const mapGroupStats = computed(() => {
  const groups = buildMapAssetGroups(mapAssets.value)

  return {
    groups: groups.length,
    overlapGroups: groups.filter((group) => group.assets.length > 1).length,
  }
})

const visibleClusterStats = ref({
  clusters: 0,
  clusterGroups: 0,
})

function updateVisibleClusterStats() {
  if (!mapClusterSource) {
    visibleClusterStats.value = {
      clusters: 0,
      clusterGroups: 0,
    }
    return
  }

  const clusterFeatures = mapClusterSource.getFeatures()
  visibleClusterStats.value = {
    clusters: clusterFeatures.length,
    clusterGroups: clusterFeatures.filter((feature) => {
      const features = feature.get('features')
      return Array.isArray(features) && features.length > 1
    }).length,
  }
}

const noGpsAssets = computed(() => {
  return assets.value.filter((item) => !itemHasGps(item))
})

const gpsAssets = computed(() => {
  return assets.value.filter((item) => itemHasGps(item))
})

const filteredAssets = computed(() => {
  if (assetFilter.value === 'gps') {
    return gpsAssets.value
  }

  if (assetFilter.value === 'no_gps') {
    return noGpsAssets.value
  }

  if (assetFilter.value === 'processed') {
    return assets.value.filter((item) => assetProcessed(item))
  }

  if (assetFilter.value === 'pending') {
    return assets.value.filter((item) => !assetProcessed(item))
  }

  return assets.value
})

const taskStats = computed(() => {
  const source = taskSummary.value?.by_status || {}

  return {
    total: taskSummary.value?.total ?? tasks.value.length,
    pending: source.pending ?? tasks.value.filter((task) => task.status === 'pending').length,
    processing: source.processing ?? tasks.value.filter((task) => task.status === 'processing').length,
    done: source.done ?? tasks.value.filter((task) => task.status === 'done').length,
    failed: source.failed ?? tasks.value.filter((task) => task.status === 'failed').length,
  }
})

const activeTaskCount = computed(() => {
  return Number(taskStats.value.pending || 0) + Number(taskStats.value.processing || 0)
})

const failedTasks = computed(() => {
  return tasks.value.filter((task) => task.status === 'failed' || Boolean(task.error_message))
})


function pointerMarkerSvgForColor(fillColor = '#2563eb') {
  return encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="34" height="44" viewBox="0 0 34 44">
  <path d="M17 42C17 42 4 26.8 4 15.8C4 7.4 9.8 2 17 2C24.2 2 30 7.4 30 15.8C30 26.8 17 42 17 42Z" fill="${fillColor}" stroke="#ffffff" stroke-width="3"/>
  <circle cx="17" cy="15.8" r="5.4" fill="#ffffff"/>
</svg>
`)
}

const markerStyle = new Style({
  image: new Icon({
    src: `data:image/svg+xml;charset=UTF-8,${pointerMarkerSvgForColor('#2563eb')}`,
    anchor: [0.5, 1],
    anchorXUnits: 'fraction',
    anchorYUnits: 'fraction',
    scale: 0.95,
  }),
})

const selectedMarkerStyle = new Style({
  image: new Icon({
    src: `data:image/svg+xml;charset=UTF-8,${pointerMarkerSvgForColor('#2563eb')}`,
    anchor: [0.5, 1],
    anchorXUnits: 'fraction',
    anchorYUnits: 'fraction',
    scale: 1.08,
  }),
})

const manualGpsDraftStyle = new Style({
  image: new Icon({
    src: `data:image/svg+xml;charset=UTF-8,${pointerMarkerSvgForColor('#f97316')}`,
    anchor: [0.5, 1],
    anchorXUnits: 'fraction',
    anchorYUnits: 'fraction',
    scale: 1.18,
  }),
  text: new Text({
    text: '补点',
    font: '800 12px sans-serif',
    fill: new Fill({ color: '#c2410c' }),
    stroke: new Stroke({ color: '#ffffff', width: 3 }),
    offsetY: -48,
  }),
})

const markerCountStyleCache = new globalThis.Map()

function markerCountLabel(count) {
  if (count > 99) {
    return '99+'
  }

  return String(count)
}

function markerStyleForCount(count, selected = false, kind = 'cluster') {
  const label = markerCountLabel(count)
  const key = `${kind}:${selected ? 'selected' : 'normal'}:${label}`

  if (!markerCountStyleCache.has(key)) {
    const fillColor = '#2563eb'
    const labelColor = selected ? '#c2410c' : '#1d4ed8'
    const scale = selected ? 1.14 : kind === 'single' ? 0.98 : 1

    markerCountStyleCache.set(key, new Style({
      image: new Icon({
        src: `data:image/svg+xml;charset=UTF-8,${pointerMarkerSvgForColor(fillColor)}`,
        anchor: [0.5, 1],
        anchorXUnits: 'fraction',
        anchorYUnits: 'fraction',
        scale,
      }),
      text: new Text({
        text: label,
        font: label.length > 2 ? '800 10px sans-serif' : '800 12px sans-serif',
        fill: new Fill({
          color: labelColor,
        }),
        stroke: new Stroke({
          color: '#ffffff',
          width: selected ? 3 : 2,
        }),
        offsetY: -27,
      }),
    }))
  }

  return markerCountStyleCache.get(key)
}

function singleMarkerLabelFromCluster(clusteredFeatures, feature) {
  const sourceFeature = Array.isArray(clusteredFeatures) && clusteredFeatures.length > 0
    ? clusteredFeatures[0]
    : feature

  const mapLabel = sourceFeature?.get('map_label')
  if (mapLabel !== undefined && mapLabel !== null && mapLabel !== '') {
    return mapLabel
  }

  const assets = featureAssets(sourceFeature)
  const asset = assets[0]
  return asset?.display_index || asset?.id || 1
}

function clusteredFeatureHasSelected(clusteredFeatures) {
  if (!selectedAssetId.value || !Array.isArray(clusteredFeatures)) {
    return false
  }

  return clusteredFeatures.some((feature) => {
    return featureAssets(feature).some((asset) => String(asset?.id) === String(selectedAssetId.value))
  })
}

function markerStyleFunction(feature) {
  const clusteredFeatures = feature.get('features')
  const count = Array.isArray(clusteredFeatures) ? clusteredFeatures.length : Number(feature.get('point_count') || 1)
  const selected = clusteredFeatureHasSelected(clusteredFeatures)

  if (count > 1) {
    return markerStyleForCount(count, selected, 'cluster')
  }

  const singleLabel = singleMarkerLabelFromCluster(clusteredFeatures, feature)
  return markerStyleForCount(singleLabel, selected, 'single')
}

function parseCoordinate(value) {
  if (value === null || value === undefined || value === '') {
    return null
  }

  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function isValidMapAsset(item) {
  const latitude = parseCoordinate(item?.latitude)
  const longitude = parseCoordinate(item?.longitude)

  return (
    latitude !== null &&
    longitude !== null &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180
  )
}

function assetCoordinateText(item) {
  if (!isValidMapAsset(item)) {
    return '-'
  }

  const latitude = parseCoordinate(item.latitude)
  const longitude = parseCoordinate(item.longitude)

  return `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`
}

function mapCoordinateKey(item) {
  const latitude = parseCoordinate(item?.latitude)
  const longitude = parseCoordinate(item?.longitude)

  if (latitude === null || longitude === null) {
    return ''
  }

  return `${latitude.toFixed(6)},${longitude.toFixed(6)}`
}

function buildMapAssetGroups(items) {
  const groupMap = new globalThis.Map()

  for (const asset of items || []) {
    if (!isValidMapAsset(asset)) {
      continue
    }

    const latitude = parseCoordinate(asset.latitude)
    const longitude = parseCoordinate(asset.longitude)
    const key = mapCoordinateKey(asset)

    if (!groupMap.has(key)) {
      groupMap.set(key, {
        key,
        latitude,
        longitude,
        coordinate: fromLonLat([longitude, latitude]),
        assets: [],
      })
    }

    groupMap.get(key).assets.push(asset)
  }

  return Array.from(groupMap.values())
}

function featureAssets(feature) {
  if (!feature) {
    return []
  }

  const assetsFromFeature = feature.get('assets')
  if (Array.isArray(assetsFromFeature) && assetsFromFeature.length > 0) {
    return assetsFromFeature
  }

  const singleAsset = feature.get('asset')
  return singleAsset ? [singleAsset] : []
}

function clusteredFeatureAssets(clusterFeature) {
  const clusteredFeatures = clusterFeature?.get('features')

  if (!Array.isArray(clusteredFeatures)) {
    return featureAssets(clusterFeature)
  }

  return clusteredFeatures.flatMap((feature) => featureAssets(feature))
}

function ensureMapMarkerLayer() {
  if (!mapMarkerSource) {
    mapMarkerSource = new VectorSource()
  }

  if (!mapClusterSource) {
    mapClusterSource = new ClusterSource({
      source: mapMarkerSource,
      distance: 52,
      minDistance: 18,
    })
  }

  if (!mapMarkerLayer) {
    mapMarkerLayer = new VectorLayer({
      source: mapClusterSource,
      style: markerStyleFunction,
    })
  }

  if (mapInstance && !mapInstance.getLayers().getArray().includes(mapMarkerLayer)) {
    mapInstance.addLayer(mapMarkerLayer)
  }

  updateVisibleClusterStats()
}

function ensureManualGpsLayer() {
  if (!manualGpsSource) {
    manualGpsSource = new VectorSource()
  }

  if (!manualGpsLayer) {
    manualGpsLayer = new VectorLayer({
      source: manualGpsSource,
      style: manualGpsDraftStyle,
    })
  }

  if (mapInstance && !mapInstance.getLayers().getArray().includes(manualGpsLayer)) {
    mapInstance.addLayer(manualGpsLayer)
  }
}

function clearManualGpsDraftMarker() {
  if (manualGpsSource) {
    manualGpsSource.clear()
  }
}

function updateManualGpsDraftMarker(coordinate) {
  ensureManualGpsLayer()

  if (!manualGpsSource) {
    return
  }

  manualGpsSource.clear()
  const feature = new Feature({
    geometry: new Point(coordinate),
  })
  feature.set('manual_draft', true)
  manualGpsSource.addFeature(feature)
}

function setupMapClickHandler() {
  if (!mapInstance || mapClickReady) {
    return
  }

  mapClickReady = true

  mapInstance.on('singleclick', async (event) => {
    if (manualGpsAsset.value) {
      setManualGpsDraftFromMapCoordinate(event.coordinate)
      return
    }

    let selectedAssets = []

    mapInstance.forEachFeatureAtPixel(event.pixel, (feature) => {
      selectedAssets = clusteredFeatureAssets(feature)
      return true
    })

    if (selectedAssets.length > 1) {
      showMapPointGroup(selectedAssets)
    } else if (selectedAssets.length === 1) {
      await focusAssetInSidebarFromMap(selectedAssets[0], { keepZoom: true })
    }
  })

  mapInstance.on('pointermove', (event) => {
    const target = mapInstance.getTargetElement()

    if (!target) {
      return
    }

    if (manualGpsAsset.value) {
      target.style.cursor = 'crosshair'
      return
    }

    target.style.cursor = mapInstance.hasFeatureAtPixel(event.pixel) ? 'pointer' : ''
  })

  mapInstance.on('moveend', () => {
    updateVisibleClusterStats()
  })
}

function updateMapMarkers(shouldFit = false) {
  if (!mapInstance) {
    return
  }

  ensureMapMarkerLayer()

  if (!mapMarkerSource) {
    return
  }

  mapMarkerSource.clear()
  const coordinates = []

  let mapLabelIndex = 1

  for (const asset of mapAssets.value || []) {
    if (!isValidMapAsset(asset)) {
      continue
    }

    const latitude = parseCoordinate(asset.latitude)
    const longitude = parseCoordinate(asset.longitude)
    const coordinate = fromLonLat([longitude, latitude])
    const feature = new Feature({
      geometry: new Point(coordinate),
    })

    feature.set('asset', asset)
    feature.set('assets', [asset])
    feature.set('point_count', 1)
    feature.set('map_label', mapLabelIndex)
    mapLabelIndex += 1
    mapMarkerSource.addFeature(feature)
    coordinates.push(coordinate)
  }

  if (mapClusterSource) {
    mapClusterSource.refresh()
  }

  if (shouldFit && coordinates.length > 0) {
    if (coordinates.length === 1) {
      mapInstance.getView().animate({
        center: coordinates[0],
        zoom: 15,
        duration: 350,
      })
    } else {
      mapInstance.getView().fit(boundingExtent(coordinates), {
        padding: [42, 42, 42, 42],
        maxZoom: 17,
        duration: 350,
      })
    }
  }

  updateVisibleClusterStats()
  refreshMapSize()
}

async function loadMapAssets(projectId, options = {}) {
  if (!projectId) {
    mapAssets.value = []
    mapAssetsMessage.value = '尚未选择项目。'
    updateMapMarkers(false)
    return
  }

  mapAssetsLoading.value = true

  try {
    const response = await fetch(`${API_BASE}/api/projects/${projectId}/map-assets`)

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`HTTP ${response.status} ${text}`)
    }

    const data = await response.json()
    mapAssets.value = Array.isArray(data) ? data : []
    const validCount = mapAssets.value.filter((item) => isValidMapAsset(item)).length
    mapAssetsMessage.value = `地图点位已加载：${validCount} 个有效 GPS 点位，地图会按当前缩放自动聚合。`

    await nextTick()
    updateMapMarkers(options.fit === true)
  } catch (error) {
    mapAssets.value = []
    mapAssetsMessage.value = `地图点位加载失败：${error.message}`
    updateMapMarkers(false)
  } finally {
    mapAssetsLoading.value = false
  }
}

function refreshMapSize() {
  if (!mapInstance) {
    return
  }

  requestAnimationFrame(() => {
    mapInstance?.updateSize()
  })

  setTimeout(() => {
    mapInstance?.updateSize()
  }, 120)
}

function refreshMapSizeSoon() {
  nextTick(() => {
    refreshMapSize()
    setTimeout(() => refreshMapSize(), 260)
  })
}

function clampSidebarWidth(width) {
  const viewportWidth = window.innerWidth || SIDEBAR_DEFAULT_WIDTH
  const viewportLimit = Math.max(SIDEBAR_MIN_WIDTH, viewportWidth - 80)
  const dragLimit = Math.max(SIDEBAR_MIN_WIDTH, Math.min(SIDEBAR_MAX_WIDTH, Math.floor(viewportWidth * 0.6), viewportLimit))
  const numericWidth = Number(width)

  if (!Number.isFinite(numericWidth)) {
    return SIDEBAR_DEFAULT_WIDTH
  }

  return Math.round(Math.min(Math.max(numericWidth, SIDEBAR_MIN_WIDTH), dragLimit))
}

function refreshMapSizeWhileResizing() {
  if (sidebarResizeFrame) {
    return
  }

  sidebarResizeFrame = requestAnimationFrame(() => {
    sidebarResizeFrame = null
    mapInstance?.updateSize()
  })
}

function setSidebarWidth(width, { remember = true } = {}) {
  sidebarWidth.value = clampSidebarWidth(width)

  if (remember && !sidebarMaximized.value) {
    sidebarWidthBeforeMaximize.value = sidebarWidth.value
  }
}

function toggleSidebarMaximize() {
  if (!sidebarMaximized.value) {
    sidebarWidthBeforeMaximize.value = sidebarWidth.value
    sidebarMaximized.value = true
  } else {
    sidebarMaximized.value = false
    setSidebarWidth(sidebarWidthBeforeMaximize.value || SIDEBAR_DEFAULT_WIDTH)
  }

  refreshMapSizeSoon()
}

function stopSidebarResize() {
  if (!sidebarResizing.value) {
    return
  }

  sidebarResizing.value = false
  window.removeEventListener('pointermove', handleSidebarResizeMove)
  window.removeEventListener('pointerup', stopSidebarResize)
  window.removeEventListener('pointercancel', stopSidebarResize)
  refreshMapSizeSoon()
}

function handleSidebarResizeMove(event) {
  if (!sidebarResizing.value) {
    return
  }

  setSidebarWidth(event.clientX, { remember: false })
  sidebarMaximized.value = false
  sidebarWidthBeforeMaximize.value = sidebarWidth.value
  refreshMapSizeWhileResizing()
}

function startSidebarResize(event) {
  if (event.button !== undefined && event.button !== 0) {
    return
  }

  sidebarOpen.value = true
  sidebarResizing.value = true
  sidebarMaximized.value = false
  event.preventDefault()
  window.addEventListener('pointermove', handleSidebarResizeMove)
  window.addEventListener('pointerup', stopSidebarResize)
  window.addEventListener('pointercancel', stopSidebarResize)
}

function handleWindowResize() {
  setSidebarWidth(sidebarWidth.value, {
    remember: !sidebarMaximized.value,
  })
  refreshMapSizeSoon()
}

function resetSidebarWidthState() {
  sidebarMaximized.value = false
  sidebarWidth.value = clampSidebarWidth(SIDEBAR_DEFAULT_WIDTH)
  sidebarWidthBeforeMaximize.value = sidebarWidth.value
}

function toggleSidebar() {
  if (sidebarOpen.value) {
    sidebarOpen.value = false
    resetSidebarWidthState()
  } else {
    resetSidebarWidthState()
    sidebarOpen.value = true
  }
  refreshMapSizeSoon()
}

function openSidebar() {
  resetSidebarWidthState()
  sidebarOpen.value = true
  refreshMapSizeSoon()
}

function closeSidebar() {
  sidebarOpen.value = false
  resetSidebarWidthState()
  refreshMapSizeSoon()
}

function setSidebarTab(tabKey) {
  activeSidebarTab.value = tabKey

  if (!sidebarOpen.value) {
    openSidebar()
  }

  if (tabKey === 'noGps') {
    assetFilter.value = 'no_gps'
  }
}

function showPlaceholderMessage(message) {
  mapUiMessage.value = message
  mapUiPanel.value = 'message'
}

function headerPlaceholder(name) {
  showPlaceholderMessage(`${name} 功能入口暂未接入，后续版本可接入账号、权限和多语言系统。`)
}

function currentProjectExportBaseUrl() {
  if (!currentProjectId.value) {
    return ''
  }

  return `${API_BASE}/api/projects/${currentProjectId.value}/exports`
}

function safeFilenamePart(value, fallback = '项目') {
  const text = String(value || '').trim() || fallback
  return text
    .replace(/[\\/:*?"<>|\r\n\t]+/g, '_')
    .replace(/\s+/g, '_')
    .replace(/^\.+|\.+$/g, '')
    .slice(0, 60) || fallback
}

function exportTimestampForFilename() {
  const now = new Date()
  const pad = (value) => String(value).padStart(2, '0')
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    '_',
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds()),
  ].join('')
}

function currentProjectExportFilename(ext, label = '点位导出') {
  const projectName = safeFilenamePart(currentProject.value?.name, `project_${currentProjectId.value || '未选择'}`)
  return `${projectName}_${label}_${exportTimestampForFilename()}.${ext}`
}

function downloadBlobFile(blob, filename) {
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  setTimeout(() => URL.revokeObjectURL(objectUrl), 10000)
}

async function parseExportError(response) {
  try {
    const data = await response.json()
    return data?.detail || `导出失败，HTTP 状态码：${response.status}`
  } catch (error) {
    return `导出失败，HTTP 状态码：${response.status}`
  }
}

async function downloadProjectExport(ext, successText, options = {}) {
  if (!currentProjectId.value) {
    showPlaceholderMessage('请先选择一个项目，再执行导出。')
    return
  }

  const requireGps = options.requireGps ?? true
  const exportLabel = options.exportLabel || '点位导出'
  const endpoint = options.endpoint || `points.${ext}`

  if (requireGps && mapPointStats.value.valid < 1) {
    showPlaceholderMessage('当前项目没有可导出的 GPS 点位。请先上传带 GPS 的照片，或在“无GPS”标签中补点后再导出。')
    return
  }

  exportRunning.value = true

  try {
    const response = await fetch(`${currentProjectExportBaseUrl()}/${endpoint}`)

    if (!response.ok) {
      showPlaceholderMessage(await parseExportError(response))
      return
    }

    const blob = await response.blob()
    const filename = currentProjectExportFilename(ext, exportLabel)
    downloadBlobFile(blob, filename)

    const pointLine = requireGps ? `\n导出点位：${mapPointStats.value.valid} 个。` : ''
    showPlaceholderMessage(`${successText}\n\n文件名：${filename}${pointLine}`)
  } catch (error) {
    showPlaceholderMessage(`导出失败：${error?.message || String(error)}。请确认后端 API 容器正在运行。`)
  } finally {
    exportRunning.value = false
  }
}

function qgisSafeXml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function buildQgisQmlContent() {
  const projectName = qgisSafeXml(currentProjectName.value)

  return `<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34" styleCategories="Symbology|Labeling" labelsEnabled="1">
  <renderer-v2 type="singleSymbol" symbollevels="0" enableorderby="0" forceraster="0">
    <symbols>
      <symbol name="0" type="marker" alpha="1" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleMarker" enabled="1" pass="0" locked="0">
          <Option type="Map">
            <Option name="name" type="QString" value="circle"/>
            <Option name="color" type="QString" value="37,99,235,255"/>
            <Option name="outline_color" type="QString" value="255,255,255,255"/>
            <Option name="outline_width" type="QString" value="0.55"/>
            <Option name="outline_width_unit" type="QString" value="MM"/>
            <Option name="size" type="QString" value="3.20"/>
            <Option name="size_unit" type="QString" value="MM"/>
          </Option>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style fieldName="coalesce(&quot;point_no&quot;, &quot;asset_id&quot;)" isExpression="1" fontFamily="Microsoft YaHei" namedStyle="Bold" fontSize="11" fontSizeUnit="Point" fontWeight="75" textColor="15,23,42,255" previewBkgrdColor="#ffffff"/>
      <text-format multilineHeight="1" plussign="0" wrapChar=""/>
      <text-buffer bufferDraw="1" bufferSize="1.15" bufferSizeUnits="MM" bufferColor="255,255,255,255" bufferOpacity="1"/>
      <background shapeDraw="0"/>
      <shadow shadowDraw="0"/>
      <placement placement="1" dist="2.4" distUnits="MM" offsetType="0" xOffset="2.2" yOffset="-2.2" quadOffset="4"/>
      <rendering scaleVisibility="0" fontLimitPixelSize="0" minFeatureSize="0" obstacle="1" zIndex="0"/>
    </settings>
  </labeling>
  <customproperties>
    <Option type="Map">
      <Option name="photo-map-version" type="QString" value="V${APP_VERSION}"/>
      <Option name="photo-map-project" type="QString" value="${projectName}"/>
      <Option name="photo-map-note" type="QString" value="蓝色圆点 + point_no 编号标注；编号右上偏移并带白色描边。"/>
    </Option>
  </customproperties>
</qgis>
`
}

function buildQgisReadmeContent() {
  const now = new Date().toLocaleString('zh-CN', { hour12: false })

  return `工程照片地图管理系统 | QGIS 点位导出使用说明

一、项目导出信息
- 项目名称：${currentProjectName.value}
- 项目编号：${currentProject.value?.code || '-'}
- 项目 ID：${currentProjectId.value || '-'}
- 可导出 GPS 点位数量：${mapPointStats.value.valid}
- 说明生成时间：${now}
- 系统版本：V${APP_VERSION}

二、建议导出的文件
1. GeoJSON / QGIS 图层：项目名称_点位导出_日期时间.geojson
   - 推荐直接拖入 QGIS。
   - 坐标为 WGS84 经纬度，GeoJSON 坐标顺序为 longitude, latitude。

2. CSV 点位表：项目名称_点位导出_日期时间.csv
   - 可用 Excel 打开。
   - 在 QGIS 中作为分隔文本图层加载时，经度字段选 longitude，纬度字段选 latitude。

3. QGIS 样式文件：项目名称_QGIS样式_日期时间.qml
   - 先导入 GeoJSON 图层，再给该图层加载 QML 样式。
   - 样式会将点位显示为蓝色圆点，并优先用 point_no 字段显示编号。
   - 如果 point_no 为空，样式会尝试使用 asset_id 作为备用标注。
   - 编号字体已加大，并带白色描边，位置在点位右上方，适合打印时查看。

三、QGIS 推荐操作步骤
1. 打开 QGIS。
2. 先加载 OpenStreetMap 或其他底图。
3. 将 .geojson 文件拖入 QGIS。
4. 在左侧图层列表中右键点位图层。
5. 选择“属性” → “符号化” → “样式” → “加载样式”。
6. 选择同一批导出的 .qml 文件。
7. 如编号仍不明显，可进入“标注”页，把字号再调大，或调整偏移位置。
8. 保存 QGIS 工程文件 .qgz，作为本项目制图工程。

四、主要字段说明
- point_no：导出点位序号，建议用于地图编号标注。
- label：点位标签，通常为“序号 + 文件名”。
- asset_id：系统内部照片 ID。
- project_id：系统内部项目 ID。
- project_name：项目名称。
- filename：照片文件名。
- longitude：经度。
- latitude：纬度。
- gps_source：GPS 来源，常见值为 exif、manual_add、manual_update。
- gps_status：GPS 状态。

五、注意事项
- 正式归档时，建议优先使用“一键导出 QGIS 资料包 ZIP”。
- ZIP 内应包含 CSV、GeoJSON、QML 和本说明 TXT。
- 一旦开始真实工作试用，请注意备份数据库和上传原图目录。
`
}

function downloadTextFile(content, filename, mime = 'text/plain;charset=utf-8') {
  downloadBlobFile(new Blob([content], { type: mime }), filename)
}

async function fetchProjectExportBlob(endpoint) {
  const response = await fetch(`${currentProjectExportBaseUrl()}/${endpoint}`)

  if (!response.ok) {
    throw new Error(await parseExportError(response))
  }

  return response.blob()
}

function crc32ForBytes(bytes) {
  let crc = 0xffffffff
  for (let i = 0; i < bytes.length; i += 1) {
    crc ^= bytes[i]
    for (let j = 0; j < 8; j += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1))
    }
  }
  return (crc ^ 0xffffffff) >>> 0
}

function uint16(value) {
  return [value & 255, (value >>> 8) & 255]
}

function uint32(value) {
  return [value & 255, (value >>> 8) & 255, (value >>> 16) & 255, (value >>> 24) & 255]
}

function createStoreZipBlob(files) {
  const encoder = new TextEncoder()
  const localParts = []
  const centralParts = []
  let offset = 0

  files.forEach((file) => {
    const nameBytes = encoder.encode(file.name)
    const dataBytes = file.data instanceof Uint8Array ? file.data : encoder.encode(String(file.data ?? ''))
    const crc = crc32ForBytes(dataBytes)
    const localHeader = new Uint8Array([
      ...uint32(0x04034b50),
      ...uint16(20),
      ...uint16(0x0800),
      ...uint16(0),
      ...uint16(0),
      ...uint16(0),
      ...uint32(crc),
      ...uint32(dataBytes.length),
      ...uint32(dataBytes.length),
      ...uint16(nameBytes.length),
      ...uint16(0),
    ])

    localParts.push(localHeader, nameBytes, dataBytes)

    const centralHeader = new Uint8Array([
      ...uint32(0x02014b50),
      ...uint16(20),
      ...uint16(20),
      ...uint16(0x0800),
      ...uint16(0),
      ...uint16(0),
      ...uint16(0),
      ...uint32(crc),
      ...uint32(dataBytes.length),
      ...uint32(dataBytes.length),
      ...uint16(nameBytes.length),
      ...uint16(0),
      ...uint16(0),
      ...uint16(0),
      ...uint16(0),
      ...uint32(0),
      ...uint32(offset),
    ])

    centralParts.push(centralHeader, nameBytes)
    offset += localHeader.length + nameBytes.length + dataBytes.length
  })

  const centralOffset = offset
  const centralSize = centralParts.reduce((sum, part) => sum + part.length, 0)
  const endHeader = new Uint8Array([
    ...uint32(0x06054b50),
    ...uint16(0),
    ...uint16(0),
    ...uint16(files.length),
    ...uint16(files.length),
    ...uint32(centralSize),
    ...uint32(centralOffset),
    ...uint16(0),
  ])

  return new Blob([...localParts, ...centralParts, endHeader], { type: 'application/zip' })
}

function downloadCurrentProjectCsv() {
  downloadProjectExport('csv', 'CSV 点位表已生成，可用 Excel 打开，也可在 QGIS 中按 longitude / latitude 字段加载。')
}

function downloadCurrentProjectGeoJson() {
  downloadProjectExport('geojson', 'GeoJSON / QGIS 图层已生成，可直接拖入 QGIS 显示照片点位。')
}

function downloadCurrentProjectQgisStyle() {
  if (!currentProjectId.value) {
    showPlaceholderMessage('请先选择一个项目，再导出 QGIS 样式。')
    return
  }

  const filename = currentProjectExportFilename('qml', 'QGIS样式')
  downloadTextFile(buildQgisQmlContent(), filename, 'application/xml;charset=utf-8')
  showPlaceholderMessage(`QGIS 样式文件已生成。导入 GeoJSON 图层后，请在 QGIS 中给该图层加载这个 QML 文件。\n\n文件名：${filename}\n样式：蓝色圆点、point_no 编号、白色描边、右上偏移。`)
}

function downloadCurrentProjectQgisReadme() {
  if (!currentProjectId.value) {
    showPlaceholderMessage('请先选择一个项目，再导出 QGIS 使用说明。')
    return
  }

  const filename = currentProjectExportFilename('txt', 'QGIS使用说明')
  downloadTextFile(buildQgisReadmeContent(), filename)
  showPlaceholderMessage(`QGIS 使用说明已生成。建议和 CSV、GeoJSON、QML 放在同一个目录。\n\n文件名：${filename}`)
}

async function downloadCurrentProjectQgisPackage() {
  if (!currentProjectId.value) {
    showPlaceholderMessage('请先选择一个项目，再导出 QGIS 资料包。')
    return
  }

  if (mapPointStats.value.valid < 1) {
    showPlaceholderMessage('当前项目没有可导出的 GPS 点位。请先上传带 GPS 的照片，或在“无GPS”标签中补点后再导出。')
    return
  }

  exportRunning.value = true

  try {
    const [csvBlob, geoJsonBlob] = await Promise.all([
      fetchProjectExportBlob('points.csv'),
      fetchProjectExportBlob('points.geojson'),
    ])

    const encoder = new TextEncoder()
    const qmlName = currentProjectExportFilename('qml', 'QGIS样式')
    const txtName = currentProjectExportFilename('txt', 'QGIS使用说明')
    const csvName = currentProjectExportFilename('csv', '点位导出')
    const geoJsonName = currentProjectExportFilename('geojson', '点位导出')
    const zipName = currentProjectExportFilename('zip', 'QGIS资料包')

    const zipBlob = createStoreZipBlob([
      { name: csvName, data: new Uint8Array(await csvBlob.arrayBuffer()) },
      { name: geoJsonName, data: new Uint8Array(await geoJsonBlob.arrayBuffer()) },
      { name: qmlName, data: encoder.encode(buildQgisQmlContent()) },
      { name: txtName, data: encoder.encode(buildQgisReadmeContent()) },
    ])

    downloadBlobFile(zipBlob, zipName)
    showPlaceholderMessage(`QGIS 资料包已生成。压缩包内包含 CSV、GeoJSON、QML 样式和 TXT 使用说明。\n\n文件名：${zipName}\n导出点位：${mapPointStats.value.valid} 个。`)
  } catch (error) {
    showPlaceholderMessage(`QGIS 资料包导出失败：${error?.message || String(error)}。请确认后端 API 容器正在运行。`)
  } finally {
    exportRunning.value = false
  }
}

function waitForMs(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

function fitMapToPrintableProjectPoints() {
  if (!mapInstance || mapPointStats.value.valid < 1) {
    return
  }

  if (printMapOptions.value.range !== 'current_project') {
    return
  }

  updateMapMarkers(true)
}

async function captureCurrentMapImage() {
  if (!mapInstance) {
    throw new Error('地图尚未初始化。')
  }

  mapInstance.renderSync()
  await waitForMs(180)

  const size = mapInstance.getSize()
  if (!size || size.length < 2 || !size[0] || !size[1]) {
    throw new Error('地图尺寸异常，无法生成预览。')
  }

  const exportCanvas = document.createElement('canvas')
  exportCanvas.width = Math.round(size[0])
  exportCanvas.height = Math.round(size[1])

  const context = exportCanvas.getContext('2d')
  if (!context) {
    throw new Error('浏览器不支持地图截图画布。')
  }

  const canvases = mapInstance.getViewport().querySelectorAll('.ol-layer canvas, canvas.ol-layer')
  canvases.forEach((canvas) => {
    if (!canvas.width || !canvas.height) {
      return
    }

    const parent = canvas.parentNode
    const opacity = parent?.style?.opacity || canvas.style.opacity || '1'
    context.globalAlpha = Number(opacity) || 1

    const transform = canvas.style.transform
    if (transform && transform.startsWith('matrix(')) {
      const matrix = transform
        .replace(/^matrix\(/, '')
        .replace(/\)$/, '')
        .split(',')
        .map((value) => Number(value.trim()))

      if (matrix.length === 6 && matrix.every((value) => Number.isFinite(value))) {
        context.setTransform(matrix[0], matrix[1], matrix[2], matrix[3], matrix[4], matrix[5])
      } else {
        context.setTransform(1, 0, 0, 1, 0, 0)
      }
    } else {
      const width = Number.parseFloat(canvas.style.width) || canvas.width
      const height = Number.parseFloat(canvas.style.height) || canvas.height
      context.setTransform(width / canvas.width, 0, 0, height / canvas.height, 0, 0)
    }

    const backgroundColor = parent?.style?.backgroundColor
    if (backgroundColor) {
      context.fillStyle = backgroundColor
      context.fillRect(0, 0, canvas.width, canvas.height)
    }

    context.drawImage(canvas, 0, 0)
  })

  context.globalAlpha = 1
  context.setTransform(1, 0, 0, 1, 0, 0)

  return exportCanvas.toDataURL('image/png')
}

function chooseNiceScaleLength(rawMeters) {
  if (!Number.isFinite(rawMeters) || rawMeters <= 0) {
    return 100
  }

  const exponent = Math.floor(Math.log10(rawMeters))
  const base = 10 ** exponent
  const normalized = rawMeters / base

  if (normalized >= 5) return 5 * base
  if (normalized >= 2) return 2 * base
  return base
}

function formatMetersForScale(meters) {
  if (!Number.isFinite(meters) || meters <= 0) {
    return '100 m'
  }

  if (meters >= 1000) {
    const km = meters / 1000
    return `${Number.isInteger(km) ? km.toFixed(0) : km.toFixed(1)} km`
  }

  return `${Math.round(meters)} m`
}

function mapScaleInfoForPreview() {
  if (!mapInstance) {
    return { text: '0 ───── 100 m', label: '100 m', width: 120 }
  }

  const view = mapInstance.getView()
  const resolution = view.getResolution()
  const center = view.getCenter()

  if (!Number.isFinite(resolution) || !center) {
    return { text: '0 ───── 100 m', label: '100 m', width: 120 }
  }

  const [, lat] = toLonLat(center)
  const latitudeFactor = Math.max(Math.cos((lat * Math.PI) / 180), 0.15)
  const metersPerPixel = resolution * latitudeFactor
  const targetPixels = 150
  const niceMeters = chooseNiceScaleLength(metersPerPixel * targetPixels)
  const width = Math.max(74, Math.min(180, Math.round(niceMeters / metersPerPixel)))
  const label = formatMetersForScale(niceMeters)

  return {
    text: `0 ───── ${label}`,
    label,
    width,
  }
}

async function openPrintMapPreview() {
  if (!currentProjectId.value) {
    showPlaceholderMessage('请先选择项目，再生成打印地图预览。')
    return
  }

  if (mapPointStats.value.valid < 1) {
    showPlaceholderMessage('当前项目没有可打印的地图点位。请先上传带 GPS 的照片，或给无 GPS 照片补点。')
    return
  }

  printMapPreviewLoading.value = true
  showPlaceholderMessage('正在生成地图打印预览，请稍候……')

  try {
    fitMapToPrintableProjectPoints()
    await waitForMs(printMapOptions.value.range === 'current_project' ? 520 : 220)
    refreshMapSize()
    await nextTick()

    const imageUrl = await captureCurrentMapImage()
    const createdAt = new Date().toLocaleString('zh-CN', { hour12: false })
    const scaleInfo = mapScaleInfoForPreview()

    printMapPreview.value = {
      open: true,
      imageUrl,
      title: `${currentProjectName.value} 工程照片点位图`,
      createdAt,
      optionsText: printMapOptionText.value,
      pointCount: mapPointStats.value.valid,
      paperSize: printMapOptions.value.paperSize,
      orientation: printMapOptions.value.orientation,
      scaleText: scaleInfo.text,
      scaleLabel: scaleInfo.label,
      scaleBarWidth: scaleInfo.width,
    }

    showPlaceholderMessage(`地图打印预览已生成。

当前参数：${printMapOptionText.value}
点位数量：${mapPointStats.value.valid} 个。
提示：本版继续优化标题、指北针、米制比例尺和页脚样式，适合作为现场点位图预览打印。`)
  } catch (error) {
    showPlaceholderMessage(`地图打印预览生成失败：${error?.message || String(error)}。`)
  } finally {
    printMapPreviewLoading.value = false
  }
}

function closePrintMapPreview() {
  printMapPreview.value = {
    ...printMapPreview.value,
    open: false,
  }
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function printMapPreviewByBrowser() {
  if (!printMapPreview.value.imageUrl) {
    showPlaceholderMessage('尚未生成地图预览，不能打印。')
    return
  }

  const paperSize = printMapPreview.value.paperSize || 'A4'
  const orientation = printMapPreview.value.orientation || 'landscape'
  const showTitle = printMapOptions.value.showTitle
  const showScale = printMapOptions.value.showScale
  const showNorth = printMapOptions.value.showNorth

  const printWindow = window.open('', '_blank', 'width=1200,height=850')
  if (!printWindow) {
    showPlaceholderMessage('浏览器拦截了打印窗口。请允许弹出窗口后重试。')
    return
  }

  printWindow.document.write(`<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${escapeHtml(printMapPreview.value.title)}</title>
<style>
  @page { size: ${paperSize} ${orientation}; margin: 8mm; }
  * { box-sizing: border-box; }
  html, body { width: 100%; height: 100%; }
  body { margin: 0; background: #fff; color: #0f172a; font-family: "Microsoft YaHei", Arial, sans-serif; }
  .sheet { width: 100%; height: 100vh; padding: 6mm 7mm 5mm; background: #fff; display: flex; flex-direction: column; overflow: hidden; page-break-after: avoid; break-after: avoid; }
  .title { display: ${showTitle ? 'block' : 'none'}; margin: 0; text-align: center; font-size: 20px; line-height: 1.2; font-weight: 900; letter-spacing: .5px; }
  .subtitle { margin-top: 3px; padding-bottom: 5px; text-align: center; color: #475569; font-size: 11px; border-bottom: 1px solid #cbd5e1; }
  .map-wrap { position: relative; flex: 1 1 auto; min-height: 0; margin-top: 6px; border: 1px solid #94a3b8; overflow: hidden; background: #e2e8f0; }
  .map-wrap img { width: 100%; height: 100%; object-fit: contain; display: block; }
  .north { display: ${showNorth ? 'flex' : 'none'}; position: absolute; top: 12px; right: 12px; width: 42px; height: 60px; align-items: center; justify-content: center; flex-direction: column; border: 1px solid rgba(15,23,42,.18); border-radius: 10px; background: rgba(255,255,255,.92); box-shadow: 0 4px 12px rgba(15,23,42,.18); font-weight: 900; }
  .north span { font-size: 27px; line-height: .9; }
  .north strong { font-size: 13px; line-height: 1; }
  .scale { display: ${showScale ? 'block' : 'none'}; position: absolute; left: 12px; bottom: 12px; min-width: 160px; padding: 6px 8px; border: 1px solid rgba(15,23,42,.16); border-radius: 8px; background: rgba(255,255,255,.94); color: #0f172a; font-size: 10px; font-weight: 800; box-shadow: 0 3px 10px rgba(15,23,42,.15); }
  .scale-line { height: 8px; border-left: 3px solid #0f172a; border-right: 3px solid #0f172a; border-bottom: 3px solid #0f172a; margin-bottom: 4px; }
  .legend { margin-top: 5px; display: flex; align-items: center; justify-content: space-between; gap: 10px; color: #334155; font-size: 10px; line-height: 1.35; }
  .legend b { color: #0f172a; }
  .footer { margin-top: 3px; display: flex; justify-content: space-between; gap: 12px; color: #64748b; font-size: 9px; border-top: 1px solid #e2e8f0; padding-top: 3px; }
  @media print { body { background: #fff; } .sheet { height: 100vh; } }
</style>
</head>
<body>
  <div class="sheet">
    <h1 class="title">${escapeHtml(printMapPreview.value.title)}</h1>
    <div class="subtitle">项目名称：${escapeHtml(currentProjectName.value)}　点位数量：${escapeHtml(printMapPreview.value.pointCount)} 个　生成时间：${escapeHtml(printMapPreview.value.createdAt)}　纸张：${escapeHtml(paperSize)} ${escapeHtml(orientation === 'landscape' ? '横向' : '纵向')}</div>
    <div class="map-wrap">
      <img src="${printMapPreview.value.imageUrl}" alt="地图打印预览">
      <div class="north"><span>↑</span><strong>N</strong></div>
      <div class="scale"><div class="scale-line" style="width:${Number(printMapPreview.value.scaleBarWidth) || 120}px"></div>${escapeHtml(printMapPreview.value.scaleText)}</div>
    </div>
    <div class="legend">
      <span><b>图例：</b>蓝色编号点为当前项目照片 GPS 点位；编号对应照片清单中的编号。</span>
      <span>${escapeHtml(printMapPreview.value.optionsText)}</span>
    </div>
    <div class="footer">
      <span>工程照片地图管理系统 V${APP_VERSION}</span>
      <span>说明：本图由当前地图视图生成，适合阶段预览打印；高清 PDF 后续版本增强。</span>
    </div>
  </div>
  <script>window.addEventListener('load', function () { window.focus(); window.print(); });<\/script>
</body>
</html>`)
  printWindow.document.close()
}

function parsePrintPhotoLayout(layout) {
  const matched = String(layout || '2x2').match(/^(\d+)x(\d+)$/)
  if (!matched) {
    return { columns: 2, rows: 2 }
  }

  const columns = Math.min(Math.max(Number(matched[1]) || 2, 1), 9)
  const rows = Math.min(Math.max(Number(matched[2]) || 2, 1), 9)
  return { columns, rows }
}

function printPhotoPerPage(layout) {
  const { columns, rows } = parsePrintPhotoLayout(layout)
  return columns * rows
}

function printPhotoGridClass(layout) {
  return ['print-photo-grid', `layout-${layout || '2x2'}`, printPhotoDensityClass(layout)]
}

function printPhotoGridStyle(layout) {
  const { columns, rows } = parsePrintPhotoLayout(layout)
  return {
    gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
    gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))`,
  }
}

function printPaperDimensions(paperSize, orientation) {
  const isA3 = String(paperSize || 'A4').toUpperCase() === 'A3'
  const isLandscape = orientation === 'landscape'
  const pageWidth = isA3 ? (isLandscape ? 420 : 297) : (isLandscape ? 297 : 210)
  const pageHeight = isA3 ? (isLandscape ? 297 : 420) : (isLandscape ? 210 : 297)
  const margin = 8

  return {
    pageWidth,
    pageHeight,
    contentWidth: pageWidth - margin * 2,
    contentHeight: pageHeight - margin * 2,
    margin,
  }
}

function assetPrintNo(asset, index = 0) {
  return asset?.point_no || asset?.display_index || asset?.map_label || index + 1
}

function assetPrintSourceText(asset) {
  const source = gpsSourceText(asset)
  return source === '-' ? '无 GPS' : source
}

function formatPrintDate(value) {
  const text = formatDate(value)
  return text === '-' ? '无拍摄时间' : text
}

function assetPrintGpsStatusText(asset) {
  if (!itemHasGps(asset)) {
    return '无 GPS'
  }

  const rawStatus = String(
    asset?.gps_status ||
    asset?.gpsStatus ||
    asset?.gps_state ||
    asset?.gpsState ||
    '',
  ).trim()

  const status = rawStatus.toLowerCase()

  if (status.includes('edit') || status.includes('修改') || status.includes('edited')) {
    return '已修改'
  }

  if (status.includes('valid') || status.includes('ok') || status.includes('有效')) {
    return '有效'
  }

  if (status.includes('manual') || status.includes('补点')) {
    return '手动补点'
  }

  if (rawStatus) {
    return rawStatus
  }

  return '有效'
}

function assetPrintCoordinateText(asset) {
  const text = assetCoordinateText(asset)
  return text === '-' ? '无 GPS 坐标' : text
}

function assetPrintStatusText(asset) {
  return assetStatusText(asset)
}

function printPhotoDensityClass(layout) {
  const perPage = printPhotoPerPage(layout)

  if (perPage >= 36) {
    return 'density-tiny'
  }

  if (perPage >= 16) {
    return 'density-compact'
  }

  return 'density-normal'
}

function buildPrintPhotoPages(sourceAssets, layout) {
  const perPage = printPhotoPerPage(layout)
  const sortedAssets = [...sourceAssets].sort((left, right) => Number(left?.id || 0) - Number(right?.id || 0))
  const pages = []

  for (let index = 0; index < sortedAssets.length; index += perPage) {
    pages.push(sortedAssets.slice(index, index + perPage))
  }

  return pages
}

function openPrintPhotoListPreview() {
  if (!currentProjectId.value) {
    showPlaceholderMessage('请先选择项目，再生成照片清单预览。')
    return
  }

  if (assetStats.value.total < 1) {
    showPlaceholderMessage('当前项目没有照片，不能生成照片清单。')
    return
  }

  const createdAt = new Date().toLocaleString('zh-CN', { hour12: false })
  const pages = buildPrintPhotoPages(assets.value, printPhotoOptions.value.layout)

  printPhotoPreview.value = {
    open: true,
    title: `${currentProjectName.value} 工程照片清单`,
    createdAt,
    optionsText: printPhotoOptionText.value,
    paperSize: printPhotoOptions.value.paperSize,
    orientation: printPhotoOptions.value.orientation,
    layout: printPhotoOptions.value.layout,
    includeInfo: printPhotoOptions.value.includeInfo,
    includePageNo: printPhotoOptions.value.includePageNo,
    totalCount: assets.value.length,
    pages,
  }

  showPlaceholderMessage(`照片清单预览已生成。

当前参数：${printPhotoOptionText.value}
照片数量：${assets.value.length} 张。`)
}

function closePrintPhotoPreview() {
  printPhotoPreview.value = {
    ...printPhotoPreview.value,
    open: false,
  }
}

function photoPrintCardHtml(asset, index, includeInfo) {
  const imageUrl = assetPreviewUrl(asset) || assetThumbUrl(asset) || assetOriginalUrl(asset)
  const imageHtml = imageUrl
    ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(assetFilename(asset))}">`
    : '<div class="photo-empty">暂无图片</div>'

  const infoHtml = includeInfo
    ? `<div class="photo-meta">
        <div><strong>编号：</strong>${escapeHtml(assetPrintNo(asset, index))}</div>
        <div><strong>文件名：</strong>${escapeHtml(assetFilename(asset))}</div>
        <div><strong>拍摄时间：</strong>${escapeHtml(formatPrintDate(asset.shot_at))}</div>
        <div><strong>GPS：</strong>${escapeHtml(gpsText(asset))}　<strong>来源：</strong>${escapeHtml(assetPrintSourceText(asset))}</div>
        <div><strong>坐标：</strong>${escapeHtml(assetPrintCoordinateText(asset))}</div>
        <div><strong>GPS 状态：</strong>${escapeHtml(assetPrintGpsStatusText(asset))}　<strong>处理：</strong>${escapeHtml(assetPrintStatusText(asset))}</div>
      </div>`
    : ''

  return `<article class="photo-card-print">
    <div class="photo-image">${imageHtml}</div>
    ${infoHtml}
  </article>`
}

function printPhotoPreviewByBrowser() {
  if (!printPhotoPreview.value.open || printPhotoPreview.value.totalCount < 1) {
    showPlaceholderMessage('尚未生成照片清单预览，不能打印。')
    return
  }

  const paperSize = printPhotoPreview.value.paperSize || 'A4'
  const orientation = printPhotoPreview.value.orientation || 'portrait'
  const layout = printPhotoPreview.value.layout || '2x2'
  const { columns, rows } = parsePrintPhotoLayout(layout)
  const paper = printPaperDimensions(paperSize, orientation)
  const includeInfo = printPhotoPreview.value.includeInfo
  const includePageNo = printPhotoPreview.value.includePageNo
  const pages = printPhotoPreview.value.pages || []

  const printWindow = window.open('', '_blank', 'width=1200,height=850')
  if (!printWindow) {
    showPlaceholderMessage('浏览器拦截了打印窗口。请允许弹出窗口后重试。')
    return
  }

  const pagesHtml = pages.map((pageAssets, pageIndex) => {
    const startIndex = pages.slice(0, pageIndex).reduce((sum, page) => sum + page.length, 0)
    const cards = pageAssets.map((asset, itemIndex) => photoPrintCardHtml(asset, startIndex + itemIndex, includeInfo)).join('')
    const pageNo = includePageNo ? `<div class="page-no">第 ${pageIndex + 1} 页 / 共 ${pages.length} 页</div>` : ''

    return `<section class="sheet">
      <header>
        <h1>${escapeHtml(printPhotoPreview.value.title)}</h1>
        <div class="subtitle">
          <span>项目名称：${escapeHtml(currentProjectName.value)}</span>
          <span>照片总数：${escapeHtml(printPhotoPreview.value.totalCount)} 张</span>
          <span>生成时间：${escapeHtml(printPhotoPreview.value.createdAt)}</span>
          <span>版式：${escapeHtml(printPhotoPreview.value.optionsText)}</span>
        </div>
      </header>
      <div class="photo-grid layout-${escapeHtml(layout)} ${escapeHtml(printPhotoDensityClass(layout))}" style="grid-template-columns: repeat(${columns}, minmax(0, 1fr)); grid-template-rows: repeat(${rows}, minmax(0, 1fr));">${cards}</div>
      ${pageNo}
    </section>`
  }).join('')

  printWindow.document.write(`<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${escapeHtml(printPhotoPreview.value.title)}</title>
<style>
  @page { size: ${paperSize} ${orientation}; margin: ${paper.margin}mm; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { background: #f1f5f9; color: #0f172a; font-family: "Microsoft YaHei", Arial, sans-serif; }
  .sheet { width: ${paper.contentWidth}mm; height: ${paper.contentHeight}mm; margin: 0 auto 14px; padding: 0; background: #fff; page-break-after: always; break-after: page; display: flex; flex-direction: column; gap: 5px; overflow: hidden; }
  .sheet:last-child { page-break-after: auto; break-after: auto; }
  h1 { margin: 0; text-align: center; font-size: 15px; line-height: 1.25; color: #0f172a; letter-spacing: .5px; }
  .subtitle { display: flex; flex-wrap: wrap; justify-content: center; gap: 3px 12px; text-align: center; color: #475569; font-size: 8px; line-height: 1.35; }
  header { flex: 0 0 auto; padding-top: 1mm; padding-bottom: 1mm; border-bottom: 1px solid #e2e8f0; }
  .photo-grid { flex: 1 1 auto; display: grid; gap: 2.5mm; min-height: 0; overflow: hidden; }
  .photo-grid.density-compact { gap: 1.8mm; }
  .photo-grid.density-tiny { gap: 1mm; }
  .photo-card-print { min-height: 0; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; display: flex; flex-direction: column; background: #fff; break-inside: avoid; page-break-inside: avoid; }
  .photo-grid.density-compact .photo-card-print,
  .photo-grid.density-tiny .photo-card-print { border-radius: 4px; }
  .photo-image { flex: 1 1 auto; min-height: 0; display: flex; align-items: center; justify-content: center; background: #020617; }
  .photo-image img { width: 100%; height: 100%; object-fit: contain; display: block; }
  .photo-empty { color: #94a3b8; font-size: 12px; }
  .photo-meta { flex: 0 0 auto; padding: 4px 6px; border-top: 1px solid #e2e8f0; background: #f8fafc; color: #334155; font-size: 8.5px; line-height: 1.28; word-break: break-all; }
  .photo-grid.density-compact .photo-meta { padding: 3px 4px; font-size: 7px; line-height: 1.2; }
  .photo-grid.density-tiny .photo-meta { padding: 2px 3px; font-size: 5.8px; line-height: 1.12; }
  .photo-meta div { margin: 0; }
  .page-no { flex: 0 0 auto; text-align: center; color: #64748b; font-size: 8px; line-height: 1.2; }
  @media screen { body { padding: 12px; } .sheet { box-shadow: 0 10px 30px rgba(15,23,42,.16); } }
  @media print { body { background: #fff; } .sheet { margin: 0; box-shadow: none; } }
</style>
</head>
<body>
  ${pagesHtml}
  <script>window.addEventListener('load', function () { window.focus(); setTimeout(function(){ window.print(); }, 350); });<\/script>
</body>
</html>`)
  printWindow.document.close()
}

function showPrintPackageEntryMessage() {
  if (!currentProjectId.value) {
    showPlaceholderMessage('请先选择项目，再查看打印资料包说明。')
    return
  }

  const createdAt = new Date().toLocaleString('zh-CN', { hour12: false })
  printPackagePreview.value = {
    open: true,
    title: `${currentProjectName.value} - 打印资料包说明`,
    createdAt,
    mapOptionsText: printMapOptionText.value,
    photoOptionsText: printPhotoOptionText.value,
    totalPhotos: assetStats.value.total,
    gpsPhotos: assetStats.value.gps,
    noGpsPhotos: assetStats.value.noGps,
    mapPoints: mapPointStats.value.valid,
    packageFiles: [
      '地图打印预览：当前已支持浏览器打印，后续版本可生成地图 PDF。',
      '照片清单预览：当前已支持 1×1 到 9×9 版式浏览器打印。',
      '点位数据：可复用 CSV / GeoJSON / QGIS 资料包中的点位文件。',
      '打印说明：后续版本可打包 TXT 说明、地图 PDF、照片清单 PDF。',
    ],
    nextSteps: [
      'QGIS 资料包已可导出；QML 样式可作为初始样式，必要时可在 QGIS 中手工微调。',
      '后续版本正式实现地图 PDF、照片清单 PDF、打印资料包 ZIP。',
      '打印资料包会优先服务竣工资料、现场汇报和项目归档。',
    ],
  }

  showPlaceholderMessage(`打印资料包说明已打开。

当前项目：${currentProjectName.value}
照片：${assetStats.value.total} 张，地图点位：${mapPointStats.value.valid} 个。`)
}

function closePrintPackagePreview() {
  printPackagePreview.value = {
    ...printPackagePreview.value,
    open: false,
  }
}



function runMapSearch() {
  const keyword = mapSearchKeyword.value.trim()
  if (!keyword) {
    showPlaceholderMessage('请输入照片名称、编号、道路名称或备注关键词。搜索接口后续版本接入。')
    return
  }

  showPlaceholderMessage(`已收到搜索关键词：“${keyword}”。后续版本会按照片文件名、项目名称、标识、备注和坐标进行检索定位。`)
}

function zoomMapBy(delta) {
  if (!mapInstance) {
    return
  }

  const view = mapInstance.getView()
  const currentZoom = Number(view.getZoom() || 0)
  view.animate({
    zoom: currentZoom + delta,
    duration: 180,
  })
}

function zoomMapIn() {
  zoomMapBy(1)
}

function zoomMapOut() {
  zoomMapBy(-1)
}

function locateCurrentPosition() {
  if (!navigator.geolocation) {
    showPlaceholderMessage('当前浏览器不支持定位功能。')
    return
  }

  mapUiMessage.value = '正在读取当前位置……'
  mapUiPanel.value = 'message'

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const longitude = position.coords.longitude
      const latitude = position.coords.latitude
      const coordinate = fromLonLat([longitude, latitude])

      if (mapInstance) {
        mapInstance.getView().animate({
          center: coordinate,
          zoom: 17,
          duration: 420,
        })
      }

      mapUiMessage.value = `已定位到当前位置：${latitude.toFixed(6)}, ${longitude.toFixed(6)}`
    },
    (error) => {
      mapUiMessage.value = `读取当前位置失败：${error.message || '浏览器未授权定位'}`
    },
    {
      enableHighAccuracy: true,
      timeout: 8000,
      maximumAge: 30000,
    },
  )
}

function toggleMapPanel(panelName) {
  mapUiPanel.value = mapUiPanel.value === panelName ? null : panelName
}

function closeMapPanel() {
  mapUiPanel.value = null
}

function setBasemap(key) {
  activeBasemap.value = key
  const item = basemapOptions.find((option) => option.key === key)
  mapUiMessage.value = `${item?.name || '底图'} 已选中。当前版本先保留入口，后续版本接入多底图瓦片源。`
}

function initMap() {
  if (!mapTarget.value) {
    return
  }

  if (mapInstance) {
    mapInstance.setTarget(mapTarget.value)
    ensureMapMarkerLayer()
    ensureManualGpsLayer()
    updateMapMarkers(false)
    refreshMapSize()
    return
  }

  mapInstance = new Map({
    target: mapTarget.value,
    layers: [
      new TileLayer({
        source: new OSM(),
      }),
    ],
    view: new View({
      center: fromLonLat([113.3077, 33.735]),
      zoom: 10,
    }),
  })

  mapInstance.addControl(new ScaleLine({
    units: 'metric',
    minWidth: 92,
  }))

  ensureMapMarkerLayer()
  ensureManualGpsLayer()
  setupMapClickHandler()
  updateMapMarkers(false)
  refreshMapSize()
}

function detachMap() {
  if (!mapInstance) {
    return
  }

  mapInstance.setTarget(undefined)
}

async function restoreHomeMap() {
  await nextTick()
  initMap()
  refreshMapSize()

  setTimeout(() => {
    refreshMapSize()
  }, 300)
}

function formatDate(value) {
  if (!value) {
    return '-'
  }

  const text = String(value)
  return text.replace('T', ' ').replace(/\.\d+$/, '')
}

function safeJson(value) {
  if (!value) {
    return '{}'
  }

  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function mediaUrl(value) {
  if (!value || value === '-') {
    return ''
  }

  const text = String(value)

  if (text.startsWith('http://') || text.startsWith('https://')) {
    return text
  }

  if (text.startsWith('/media/')) {
    return `${API_BASE}${text}`
  }

  if (text.startsWith('media/')) {
    return `${API_BASE}/${text}`
  }

  return `${API_BASE}/media/${text}`
}

function openMedia(value) {
  const url = mediaUrl(value)

  if (!url) {
    alert('暂无可打开的图片地址')
    return
  }

  window.open(url, '_blank')
}

function itemHasGps(item) {
  return item?.has_gps === true || item?.has_gps === 'true' || item?.gps === true || isValidMapAsset(item)
}

function assetProcessed(item) {
  return Boolean(item?.thumb_url || item?.preview_url || item?.thumb_path || item?.preview_path)
}

function assetFilename(item) {
  return item?.filename || item?.original_filename || item?.name || `asset-${item?.id || ''}`
}

function assetThumbUrl(item) {
  return mediaUrl(item?.thumb_url || item?.thumb_path)
}

function assetPreviewUrl(item) {
  return mediaUrl(item?.preview_url || item?.preview_path || item?.original_url || item?.storage_path)
}

function assetOriginalUrl(item) {
  return mediaUrl(item?.original_url || item?.storage_path)
}

function assetStatusText(item) {
  if (assetProcessed(item)) {
    return '处理完成'
  }

  return '等待处理/旧照片'
}

function assetStatusClass(item) {
  if (assetProcessed(item)) {
    return 'badge-success'
  }

  return 'badge-muted'
}

function gpsText(item) {
  return itemHasGps(item) ? '是' : '否'
}

function gpsSourceText(item) {
  if (!itemHasGps(item)) {
    return '-'
  }

  const rawSource = String(
    item?.gps_source ||
    item?.gpsSource ||
    item?.gps_origin ||
    item?.gpsOrigin ||
    item?.source ||
    '',
  ).trim()

  const source = rawSource.toLowerCase()

  if (source.includes('manual') || source.includes('hand') || source.includes('补点')) {
    return '手动补点'
  }

  if (source.includes('edit') || source.includes('modify') || source.includes('update') || source.includes('修正') || source.includes('修改')) {
    return '手动修改'
  }

  if (source.includes('exif') || source.includes('photo') || source.includes('camera') || source.includes('相机')) {
    return 'EXIF'
  }

  if (rawSource) {
    return rawSource
  }

  return '未知/历史数据'
}


function gpsStatusText(item) {
  if (!itemHasGps(item)) {
    return '无 GPS'
  }

  const sourceText = gpsSourceText(item)
  const rawStatus = String(
    item?.gps_status ||
    item?.gpsStatus ||
    item?.gps_state ||
    item?.gpsState ||
    '',
  ).trim()
  const status = rawStatus.toLowerCase()

  if (sourceText === '手动修改' || status.includes('edit') || status.includes('modify') || status.includes('update') || status.includes('修改')) {
    return '已修改'
  }

  if (sourceText === '手动补点' || status.includes('manual') || status.includes('补点')) {
    return '手动补点'
  }

  if (status.includes('valid') || status.includes('ok') || status.includes('有效')) {
    return '有效'
  }

  return rawStatus || '有效'
}

function shotTimeText(item) {
  return item?.shot_at ? '有' : '无'
}

function setAssetFilter(value) {
  assetFilter.value = value
}

function toggleAssetDetail(assetId) {
  const next = new Set(expandedAssetIds.value)

  if (next.has(assetId)) {
    next.delete(assetId)
  } else {
    next.add(assetId)
  }

  expandedAssetIds.value = next
}

function isAssetExpanded(assetId) {
  return expandedAssetIds.value.has(assetId)
}

function showPreview(asset) {
  previewAsset.value = asset
}

function closePreview() {
  previewAsset.value = null
}

function showMapPointGroup(assetList) {
  mapPointGroupAssets.value = Array.isArray(assetList) ? assetList : []
}

function closeMapPointGroup() {
  mapPointGroupAssets.value = []
}

function openMapPointGroupAsset(asset) {
  closeMapPointGroup()
  selectAsset(asset)
  showPreview(asset)
}

async function focusAssetInSidebarFromMap(asset, options = {}) {
  if (!asset) {
    return
  }

  // 地图点位点击只负责“定位和选择”，不直接弹出大图预览。
  // 大图预览仍然保留在左侧照片卡片的“查看预览”按钮里。
  closePreview()
  activeSidebarTab.value = 'photos'

  if (!sidebarOpen.value) {
    openSidebar()
  } else {
    refreshMapSizeSoon()
  }

  await nextTick()
  await focusMapOnAsset(asset, {
    scrollList: true,
    keepZoom: options.keepZoom === true,
  })
}

function assetDomId(assetOrId) {
  const id = typeof assetOrId === 'object' ? assetOrId?.id : assetOrId
  return `asset-card-${id}`
}

function isSelectedAsset(asset) {
  return selectedAssetId.value !== null && String(asset?.id) === String(selectedAssetId.value)
}

function refreshMarkerStyles() {
  if (mapMarkerLayer) {
    mapMarkerLayer.changed()
  }
}

function selectAsset(asset) {
  selectedAssetId.value = asset?.id ?? null
  refreshMarkerStyles()
}

async function selectSidebarAsset(asset) {
  if (!asset) {
    return
  }

  // 左侧照片卡片点击只负责选择、定位和高亮，不直接弹出大图预览。
  // 大图预览统一保留给“查看预览”按钮。
  closePreview()
  selectAsset(asset)

  if (isValidMapAsset(asset)) {
    await focusMapOnAsset(asset, { keepZoom: true })
  } else {
    uploadMessage.value = '这张照片没有有效 GPS，已选中照片，但暂时不能定位到地图。'
  }
}

async function scrollAssetIntoView(asset) {
  if (!asset?.id) {
    return
  }

  if (!filteredAssets.value.some((item) => String(item.id) === String(asset.id))) {
    assetFilter.value = 'all'
  }

  await nextTick()

  const element = document.getElementById(assetDomId(asset))
  if (element) {
    element.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    })
  }
}

async function focusMapOnAsset(asset, options = {}) {
  if (!asset || !isValidMapAsset(asset)) {
    uploadMessage.value = '这张照片没有有效 GPS，暂时不能定位到地图。'
    return
  }

  selectAsset(asset)

  const latitude = parseCoordinate(asset.latitude)
  const longitude = parseCoordinate(asset.longitude)
  const coordinate = fromLonLat([longitude, latitude])

  if (mapInstance) {
    const view = mapInstance.getView()
    const currentZoom = Number(view.getZoom() || 0)
    const targetZoom = options.keepZoom ? currentZoom : Math.max(currentZoom, 17)

    view.animate({
      center: coordinate,
      zoom: targetZoom,
      duration: 380,
    })
  }

  if (options.scrollList) {
    await scrollAssetIntoView(asset)
  }
}

async function locateMapPointFromGroup(asset) {
  closeMapPointGroup()
  await focusAssetInSidebarFromMap(asset)
}

function roundGpsCoordinate(value) {
  return Math.round(Number(value) * 1000000) / 1000000
}

function startManualGps(asset) {
  if (!currentProject.value?.id) {
    manualGpsMessage.value = '请先选择当前项目，再给照片补 GPS。'
    return
  }

  manualGpsAsset.value = asset
  manualGpsDraft.value = null
  manualGpsSaving.value = false
  selectedAssetId.value = asset?.id ?? null
  refreshMarkerStyles()
  clearManualGpsDraftMarker()

  activeSidebarTab.value = 'noGps'
  openSidebar()
  closeMapPointGroup()

  manualGpsMessage.value = `正在给 #${asset?.id} ${assetFilename(asset)} 补 GPS：请在地图上点击照片实际位置，或使用“取地图中心”。`
  mapUiMessage.value = '无 GPS 补点模式已开启：请在地图上点击实际位置，橙色临时指针就是待保存坐标。'
  mapUiPanel.value = 'message'
}

function cancelManualGps(message = '已取消补点。') {
  manualGpsAsset.value = null
  manualGpsDraft.value = null
  manualGpsSaving.value = false
  clearManualGpsDraftMarker()
  manualGpsMessage.value = message

  if (mapUiPanel.value === 'message') {
    mapUiMessage.value = message
  }
}

function setManualGpsDraftFromMapCoordinate(coordinate) {
  if (!manualGpsAsset.value || !coordinate) {
    return
  }

  const [longitude, latitude] = toLonLat(coordinate)
  const safeLatitude = roundGpsCoordinate(latitude)
  const safeLongitude = roundGpsCoordinate(longitude)

  if (safeLatitude < -90 || safeLatitude > 90 || safeLongitude < -180 || safeLongitude > 180) {
    manualGpsMessage.value = '所选坐标超出合法经纬度范围，请重新点击地图。'
    return
  }

  manualGpsDraft.value = {
    latitude: safeLatitude,
    longitude: safeLongitude,
  }

  updateManualGpsDraftMarker(fromLonLat([safeLongitude, safeLatitude]))
  manualGpsMessage.value = `已选补点坐标：${safeLatitude.toFixed(6)}, ${safeLongitude.toFixed(6)}。确认无误后点击“保存补点”。`
  mapUiMessage.value = manualGpsMessage.value
}

function useMapCenterForManualGps() {
  if (!manualGpsAsset.value) {
    manualGpsMessage.value = '请先在无 GPS 照片列表里选择一张照片。'
    return
  }

  const center = mapInstance?.getView().getCenter()

  if (!center) {
    manualGpsMessage.value = '地图尚未初始化，不能读取地图中心。'
    return
  }

  setManualGpsDraftFromMapCoordinate(center)
}

function normalizeManualGpsSavedAsset(savedAsset, fallbackAsset, draft) {
  return {
    ...(fallbackAsset || {}),
    ...(savedAsset || {}),
    id: savedAsset?.id || fallbackAsset?.id,
    latitude: savedAsset?.latitude ?? draft?.latitude,
    longitude: savedAsset?.longitude ?? draft?.longitude,
    has_gps: true,
    gps: true,
    gps_source: savedAsset?.gps_source || 'manual',
    gps_status: savedAsset?.gps_status || 'valid',
  }
}

function replaceAssetById(list, targetAsset) {
  if (!targetAsset?.id || !Array.isArray(list)) {
    return list
  }

  const targetId = String(targetAsset.id)
  let replaced = false
  const nextList = list.map((item) => {
    if (String(item?.id) !== targetId) {
      return item
    }

    replaced = true
    return {
      ...item,
      ...targetAsset,
    }
  })

  return replaced ? nextList : [targetAsset, ...nextList]
}

function syncSavedManualGpsAsset(targetAsset) {
  if (!targetAsset?.id) {
    return
  }

  assets.value = replaceAssetById(assets.value, targetAsset)
  mapAssets.value = replaceAssetById(mapAssets.value, targetAsset)
  updateMapMarkers(false)
}

async function saveManualGps() {
  if (!currentProject.value?.id || !manualGpsAsset.value?.id) {
    manualGpsMessage.value = '缺少当前项目或照片信息，不能保存补点。'
    return
  }

  if (!manualGpsDraft.value) {
    manualGpsMessage.value = '请先在地图上点击一个位置，或点击“取地图中心”。'
    return
  }

  manualGpsSaving.value = true

  try {
    const payload = {
      latitude: manualGpsDraft.value.latitude,
      longitude: manualGpsDraft.value.longitude,
      gps_source: 'manual',
      gps_status: 'valid',
    }

    const response = await fetch(`${API_BASE}/api/projects/${currentProject.value.id}/assets/${manualGpsAsset.value.id}/gps`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`保存补点失败：HTTP ${response.status} ${text}`)
    }

    const savedAsset = await response.json()
    const normalizedAsset = normalizeManualGpsSavedAsset(savedAsset, manualGpsAsset.value, manualGpsDraft.value)
    const savedAssetId = normalizedAsset.id
    const successMessage = `补点已保存：#${savedAssetId} ${assetFilename(normalizedAsset)}。`

    manualGpsAsset.value = null
    manualGpsDraft.value = null
    clearManualGpsDraftMarker()

    await loadAssets(currentProject.value.id)
    await loadMapAssets(currentProject.value.id, { fit: false })
    syncSavedManualGpsAsset(normalizedAsset)

    const targetAsset = mapAssets.value.find((item) => String(item.id) === String(savedAssetId)) || normalizedAsset
    selectedAssetId.value = savedAssetId
    refreshMarkerStyles()

    if (targetAsset && isValidMapAsset(targetAsset)) {
      await focusMapOnAsset(targetAsset, { keepZoom: false })
    }

    manualGpsMessage.value = `${successMessage} GPS 来源：${gpsSourceText(targetAsset)}。`
    mapUiMessage.value = `${successMessage} 已转为蓝色正式点位，列表和地图点位已刷新。`
    mapUiPanel.value = 'message'
  } catch (error) {
    manualGpsMessage.value = error.message
  } finally {
    manualGpsSaving.value = false
  }
}

async function loadProjects() {
  try {
    const response = await fetch(`${API_BASE}/api/projects`)

    if (!response.ok) {
      throw new Error(`读取项目失败：HTTP ${response.status}`)
    }

    const data = await response.json()
    projects.value = Array.isArray(data) ? data : []

    projectMessage.value = `已加载 ${projects.value.length} 个项目。`

    if (!currentProject.value && projects.value.length > 0) {
      currentProject.value = projects.value[0]
    }
  } catch (error) {
    projectMessage.value = error.message
  }
}

async function createProject() {
  const name = projectForm.value.name.trim()

  if (!name) {
    projectMessage.value = '请先填写项目名称。'
    return
  }

  try {
    const payload = {
      name,
      code: projectForm.value.code.trim(),
      project_code: projectForm.value.code.trim(),
      description: projectForm.value.description.trim(),
    }

    const response = await fetch(`${API_BASE}/api/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`创建项目失败：HTTP ${response.status} ${text}`)
    }

    const data = await response.json()

    projectForm.value = {
      name: '',
      code: '',
      description: '',
    }

    projectMessage.value = `项目创建成功：${data.name || name}`

    await loadProjects()

    const createdId = data.id
    const found = projects.value.find((item) => item.id === createdId)

    if (found) {
      currentProject.value = found
    }
  } catch (error) {
    projectMessage.value = error.message
  }
}

async function setCurrentProject(project) {
  currentProject.value = project
  uploadMessage.value = ''
  taskMessage.value = ''
  trackedTaskMessage.value = ''
  trackedTask.value = null
  trackedTaskId.value = null
  selectedAssetId.value = null
  cancelManualGps('已切换项目，补点模式已退出。')
  refreshMarkerStyles()

  await loadAssets(project.id)
  await refreshAllTaskData()
}

async function loadAssets(projectId) {
  if (!projectId) {
    assets.value = []
    await loadMapAssets(null)
    return
  }

  try {
    const response = await fetch(`${API_BASE}/api/projects/${projectId}/assets`)

    if (!response.ok) {
      throw new Error(`读取照片列表失败：HTTP ${response.status}`)
    }

    const data = await response.json()
    assets.value = Array.isArray(data) ? data : []
    uploadMessage.value = `已加载 ${assets.value.length} 张照片记录。`
    await loadMapAssets(projectId, { fit: true })
  } catch (error) {
    uploadMessage.value = error.message
  }
}

function handleFileChange(event) {
  selectedFiles.value = Array.from(event.target.files || [])
}

function extractTaskIds(data) {
  const ids = []

  if (!data) {
    return ids
  }

  if (data.task_id) {
    ids.push(data.task_id)
  }

  if (Array.isArray(data.task_ids)) {
    for (const id of data.task_ids) {
      if (id) {
        ids.push(id)
      }
    }
  }

  if (data.task?.id) {
    ids.push(data.task.id)
  }

  if (data.task?.task_id) {
    ids.push(data.task.task_id)
  }

  if (Array.isArray(data.tasks)) {
    for (const task of data.tasks) {
      if (task?.id) {
        ids.push(task.id)
      } else if (task?.task_id) {
        ids.push(task.task_id)
      }
    }
  }

  if (Array.isArray(data.assets)) {
    for (const asset of data.assets) {
      if (asset?.task_id) {
        ids.push(asset.task_id)
      }
    }
  }

  return [...new Set(ids)]
}

async function uploadPhotos() {
  if (!currentProject.value?.id) {
    uploadMessage.value = '请先选择一个项目，然后再上传照片。'
    return
  }

  if (selectedFiles.value.length === 0) {
    uploadMessage.value = '请先选择照片文件。'
    return
  }

  uploading.value = true
  uploadMessage.value = '正在上传照片……'
  const uploadCount = selectedFiles.value.length

  try {
    const formData = new FormData()

    for (const file of selectedFiles.value) {
      formData.append('files', file)
      formData.append('file', file)
    }

    const response = await fetch(`${API_BASE}/api/projects/${currentProject.value.id}/assets/upload`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(`上传失败：HTTP ${response.status} ${text}`)
    }

    const data = await response.json()
    const taskIds = extractTaskIds(data)

    selectedFiles.value = []

    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }

    uploadMessage.value = `上传完成：成功 ${data.created ?? data.count ?? uploadCount} 张。后台 worker 处理完成后，列表会自动更新。`

    await loadAssets(currentProject.value.id)
    await refreshAllTaskData()
    startSmartPolling('上传完成，已自动启动任务状态智能轮询。')

    if (taskIds.length > 0) {
      const lastTaskId = taskIds[taskIds.length - 1]
      await startTrackedTaskPolling(lastTaskId)
    } else {
      trackedTaskMessage.value = '照片已上传，正在通过任务状态中心自动轮询处理结果。'
    }
  } catch (error) {
    uploadMessage.value = error.message
  } finally {
    uploading.value = false
  }
}

function taskQueryParams() {
  const params = new URLSearchParams()

  if (taskScope.value === 'current' && currentProject.value?.id) {
    params.set('project_id', String(currentProject.value.id))
  }

  if (taskStatusFilter.value !== 'all') {
    params.set('status', taskStatusFilter.value)
  }

  return params.toString()
}

async function refreshTasks() {
  try {
    const query = taskQueryParams()
    const url = query ? `${API_BASE}/api/tasks?${query}` : `${API_BASE}/api/tasks`

    const response = await fetch(url)

    if (!response.ok) {
      throw new Error(`读取任务列表失败：HTTP ${response.status}`)
    }

    const data = await response.json()
    tasks.value = Array.isArray(data) ? data : []
    syncTrackedTaskFromTaskList()

    const scopeText = taskScope.value === 'current' ? '当前项目' : '全部项目'
    const filterText = taskStatusFilter.value === 'all' ? '全部状态' : taskStatusName(taskStatusFilter.value)

    taskMessage.value = `已加载 ${tasks.value.length} 条任务记录。范围：${scopeText}；筛选：${filterText}。`
  } catch (error) {
    taskMessage.value = error.message
  }
}

async function refreshTaskSummary() {
  try {
    const params = new URLSearchParams()

    if (taskScope.value === 'current' && currentProject.value?.id) {
      params.set('project_id', String(currentProject.value.id))
    }

    const query = params.toString()
    const url = query ? `${API_BASE}/api/tasks/summary?${query}` : `${API_BASE}/api/tasks/summary`

    const response = await fetch(url)

    if (!response.ok) {
      throw new Error(`读取任务汇总失败：HTTP ${response.status}`)
    }

    taskSummary.value = await response.json()
  } catch {
    taskSummary.value = null
  }
}

async function refreshAllTaskData() {
  await refreshTaskSummary()
  await refreshTasks()
}

function syncTrackedTaskFromTaskList() {
  if (!trackedTaskId.value) {
    return
  }

  const found = tasks.value.find((task) => {
    return (
      String(task.id) === String(trackedTaskId.value) ||
      String(task.celery_task_id) === String(trackedTaskId.value)
    )
  })

  if (found) {
    trackedTask.value = found
  }
}

async function refreshAssetsForCurrentProject() {
  if (currentProject.value?.id) {
    await loadAssets(currentProject.value.id)
  }
}

function startSmartPolling(message = '已启动任务状态智能轮询。') {
  smartPollingMessage.value = message
  smartPollingRunning.value = true

  if (smartPollingTimer) {
    return
  }

  runSmartPollingTick(true)

  smartPollingTimer = setInterval(() => {
    runSmartPollingTick(false)
  }, 2500)
}

function stopSmartPolling(message = '智能轮询空闲。') {
  if (smartPollingTimer) {
    clearInterval(smartPollingTimer)
    smartPollingTimer = null
  }

  smartPollingRunning.value = false
  smartPollingMessage.value = message
}

async function runSmartPollingTick(forceRefreshAssets = false) {
  if (smartPollingBusy) {
    return
  }

  smartPollingBusy = true

  try {
    await refreshAllTaskData()

    smartPollingLastRefresh.value = formatDate(new Date().toISOString())
    const activeCount = activeTaskCount.value

    if (forceRefreshAssets || activeCount > 0) {
      await refreshAssetsForCurrentProject()
    }

    if (activeCount > 0) {
      smartPollingRunning.value = true
      smartPollingMessage.value = `智能轮询中：还有 ${activeCount} 个后台任务正在等待或处理中。`
      return
    }

    if (smartPollingTimer) {
      await refreshAssetsForCurrentProject()
      stopSmartPolling('后台任务已全部结束，照片列表已自动刷新，智能轮询已停止。')
    } else {
      smartPollingMessage.value = '当前没有等待中/处理中的任务，智能轮询空闲。'
    }
  } catch (error) {
    smartPollingMessage.value = `智能轮询刷新失败：${error.message}`
  } finally {
    smartPollingBusy = false
  }
}

async function getTaskById(taskId) {
  const response = await fetch(`${API_BASE}/api/tasks/${taskId}`)

  if (!response.ok) {
    throw new Error(`查询任务失败：HTTP ${response.status}`)
  }

  return await response.json()
}

function stopTrackedTaskPolling() {
  if (trackedTaskTimer.value) {
    clearInterval(trackedTaskTimer.value)
    trackedTaskTimer.value = null
  }

  trackedTaskPolling.value = false
}

async function refreshAfterTaskFinished(task) {
  await refreshAllTaskData()

  if (currentProject.value?.id) {
    await loadAssets(currentProject.value.id)
  }

  if (task.status === 'done') {
    trackedTaskMessage.value = `后台处理完成：任务 #${task.id} 已完成，照片列表已刷新。`
  } else if (task.status === 'failed') {
    trackedTaskMessage.value = `后台处理失败：任务 #${task.id}，原因：${task.error_message || '未返回具体错误'}`
  }
}

async function startTrackedTaskPolling(taskId) {
  if (!taskId) {
    trackedTaskMessage.value = '已上传照片，但后端没有返回 task_id，无法自动追踪任务。'
    return
  }

  stopTrackedTaskPolling()

  trackedTaskId.value = taskId
  trackedTask.value = null
  trackedTaskPolling.value = true
  trackedTaskMessage.value = `已创建后台任务 #${taskId}，正在自动追踪处理状态……`

  const tick = async () => {
    try {
      const task = await getTaskById(taskId)
      trackedTask.value = task

      await refreshAllTaskData()

      if (task.status === 'pending') {
        trackedTaskMessage.value = `任务 #${task.id} 等待处理中……`
      } else if (task.status === 'processing') {
        trackedTaskMessage.value = `任务 #${task.id} 正在处理中，进度 ${task.progress ?? 0}%……`
      } else if (task.status === 'done' || task.status === 'failed') {
        stopTrackedTaskPolling()
        await refreshAfterTaskFinished(task)
      }
    } catch (error) {
      stopTrackedTaskPolling()
      trackedTaskMessage.value = `任务追踪失败：${error.message}`
    }
  }

  await tick()

  if (trackedTaskPolling.value) {
    trackedTaskTimer.value = setInterval(tick, 2000)
  }
}

async function setTaskScope(value) {
  taskScope.value = value
  await refreshAllTaskData()

  if (activeTaskCount.value > 0) {
    startSmartPolling('检测到当前范围内仍有后台任务，已自动保持智能轮询。')
  }
}

async function setTaskStatusFilter(value) {
  taskStatusFilter.value = value
  await refreshAllTaskData()

  if (activeTaskCount.value > 0) {
    startSmartPolling('检测到当前筛选条件下仍有后台任务，已自动保持智能轮询。')
  }
}

function taskStatusName(status) {
  const names = {
    all: '全部',
    pending: '等待中',
    processing: '处理中',
    done: '已完成',
    failed: '失败',
  }

  return names[status] || status || '-'
}

function taskStatusClass(status) {
  if (status === 'done') {
    return 'badge-success'
  }

  if (status === 'failed') {
    return 'badge-danger'
  }

  if (status === 'processing') {
    return 'badge-warning'
  }

  return 'badge-muted'
}

function taskFilename(task) {
  return task?.task_filename || task?.payload_json?.filename || task?.payload_json?.storage_path || '-'
}

function taskProjectId(task) {
  return task?.project_id || task?.payload_json?.project_id || '-'
}

function taskAssetId(task) {
  return task?.asset_id || task?.payload_json?.asset_id || '-'
}

function pickTextFromObject(value, keys) {
  if (!value || typeof value !== 'object') {
    return ''
  }

  for (const key of keys) {
    const item = value[key]

    if (typeof item === 'string' && item.trim()) {
      return item.trim()
    }

    if (item && typeof item === 'object') {
      const nested = pickTextFromObject(item, keys)

      if (nested) {
        return nested
      }
    }
  }

  return ''
}

function taskErrorText(task) {
  if (task?.error_message) {
    return String(task.error_message)
  }

  const resultText = pickTextFromObject(task?.result_json, [
    'error',
    'error_message',
    'message',
    'detail',
    'exception',
  ])

  if (resultText) {
    return resultText
  }

  if (task?.status === 'failed') {
    return '任务状态为 failed，但后端没有返回详细错误信息。'
  }

  return ''
}

function taskFailureAdvice(task) {
  const text = taskErrorText(task).toLowerCase()

  if (text.includes('exif') || text.includes('gps')) {
    return '建议检查照片 EXIF/GPS 信息是否异常，或者尝试换一张照片重新上传。'
  }

  if (text.includes('pillow') || text.includes('image') || text.includes('cannot identify')) {
    return '建议检查图片格式是否损坏，或者先用系统照片查看器打开确认图片可正常显示。'
  }

  if (text.includes('permission') || text.includes('denied')) {
    return '建议检查 data 目录权限，确认容器可以写入原图、预览图和缩略图目录。'
  }

  if (text.includes('redis') || text.includes('celery')) {
    return '建议检查 Redis 和 worker-media 容器是否正常运行。'
  }

  if (text.includes('database') || text.includes('sql') || text.includes('postgres')) {
    return '建议检查数据库连接和 assets/tasks 表记录是否正常。'
  }

  return '建议先展开任务详情，查看 payload_json 和 result_json；必要时再查看 worker-media 日志。'
}

function taskFileDisplay(task) {
  return taskFilename(task) || '-'
}

function shouldShowTaskError(task) {
  return task?.status === 'failed' || Boolean(task?.error_message) || Boolean(taskErrorText(task))
}


function syncRoute() {
  currentRoute.value = window.location.hash || '#/'
}

function navigateTo(path) {
  window.location.hash = path
  syncRoute()

  if (path === '/') {
    restoreHomeMap()
  }
}

function diagnosticStatusName(status) {
  const names = {
    ok: '正常',
    warning: '警告',
    failed: '失败',
    skipped: '跳过',
    running: '检测中',
  }

  return names[status] || status || '-'
}

function diagnosticBadgeClass(status) {
  if (status === 'ok') {
    return 'diagnostic-ok'
  }

  if (status === 'failed') {
    return 'diagnostic-failed'
  }

  if (status === 'warning') {
    return 'diagnostic-warning'
  }

  if (status === 'running') {
    return 'diagnostic-running'
  }

  return 'diagnostic-skipped'
}

function summarizeDiagnosticPayload(data) {
  if (Array.isArray(data)) {
    return `接口返回数组，共 ${data.length} 条记录。`
  }

  if (data && typeof data === 'object') {
    if (data.component === 'worker-redis') {
      const redisStatus = data.redis?.status || '-'
      const workerStatus = data.worker?.status || '-'
      const workerCount = data.worker?.online_count ?? 0
      const mediaTask = data.worker?.media_process_asset_registered ? '已注册' : '未检测到'
      return `redis=${redisStatus}；worker=${workerStatus}；在线 worker=${workerCount}；media.process_asset=${mediaTask}。`
    }

    if (data.status || data.service || data.version) {
      const parts = []

      if (data.status) {
        parts.push(`status=${data.status}`)
      }

      if (data.service) {
        parts.push(`service=${data.service}`)
      }

      if (data.version) {
        parts.push(`version=${data.version}`)
      }

      if (parts.length > 0) {
        return parts.join('；')
      }
    }

    if (typeof data.total !== 'undefined') {
      return `接口返回汇总 total=${data.total}。`
    }

    const keys = Object.keys(data)
    return `接口返回对象，字段：${keys.slice(0, 8).join('、') || '无'}。`
  }

  if (typeof data === 'string') {
    return data.slice(0, 120)
  }

  return '接口有返回内容。'
}

async function runOneDiagnostic(check) {
  if (check.skipped) {
    return {
      ...check,
      status: 'skipped',
      statusText: diagnosticStatusName('skipped'),
      detail: check.skipReason || '本项暂不检测。',
      payload: null,
      durationMs: 0,
    }
  }

  const startedAt = Date.now()
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 15000)

  try {
    const response = await fetch(`${API_BASE}${check.path}`, {
      method: check.method || 'GET',
      signal: controller.signal,
    })

    const rawText = await response.text()
    let payload = rawText

    try {
      payload = rawText ? JSON.parse(rawText) : null
    } catch {
      payload = rawText
    }

    if (!response.ok) {
      return {
        ...check,
        status: 'failed',
        statusText: diagnosticStatusName('failed'),
        detail: `HTTP ${response.status} ${response.statusText || ''}`.trim(),
        payload,
        durationMs: Date.now() - startedAt,
      }
    }

    const payloadStatus = String(payload?.status || payload?.detail?.status || '').toLowerCase()

    if (payloadStatus === 'failed' || payloadStatus === 'error') {
      return {
        ...check,
        status: 'failed',
        statusText: diagnosticStatusName('failed'),
        detail: summarizeDiagnosticPayload(payload),
        payload,
        durationMs: Date.now() - startedAt,
      }
    }

    const finalStatus = payloadStatus === 'warning' ? 'warning' : 'ok'

    return {
      ...check,
      status: finalStatus,
      statusText: diagnosticStatusName(finalStatus),
      detail: summarizeDiagnosticPayload(payload),
      payload,
      durationMs: Date.now() - startedAt,
    }
  } catch (error) {
    const isAbort = error?.name === 'AbortError'

    return {
      ...check,
      status: 'failed',
      statusText: diagnosticStatusName('failed'),
      detail: isAbort ? '请求超时：15 秒内没有收到后端响应。' : error.message,
      payload: null,
      durationMs: Date.now() - startedAt,
    }
  } finally {
    clearTimeout(timer)
  }
}

function buildDiagnosticChecks() {
  const checks = [
    {
      id: 'api-health',
      name: 'API 健康检查',
      path: '/api/health',
      description: '确认 FastAPI 后端服务是否在线，版本号和 media 目录配置是否能正常返回。',
    },
    {
      id: 'db-check',
      name: '数据库连接检查',
      path: '/api/db-check',
      description: '确认后端能否连接数据库，并执行最基础的 SELECT 1。',
    },
    {
      id: 'projects',
      name: '项目接口检查',
      path: '/api/projects',
      description: '确认项目列表接口可读，前端项目管理区依赖这个接口。',
    },
    {
      id: 'tasks',
      name: '任务列表接口检查',
      path: '/api/tasks',
      description: '确认任务状态中心可以读取后台任务列表。',
    },
    {
      id: 'tasks-summary',
      name: '任务汇总接口检查',
      path: '/api/tasks/summary',
      description: '确认任务状态中心的全部、等待中、处理中、已完成、失败等统计可用。',
    },
  ]

  if (currentProject.value?.id) {
    checks.push({
      id: 'current-assets',
      name: '当前项目照片接口检查',
      path: `/api/projects/${currentProject.value.id}/assets`,
      description: `确认当前项目“${currentProject.value.name}”的照片列表接口可读。`,
    })
  } else {
    checks.push({
      id: 'current-assets',
      name: '当前项目照片接口检查',
      path: '-',
      description: '需要先有当前项目，才能检测项目照片列表接口。',
      skipped: true,
      skipReason: '尚未选择当前项目，已跳过。',
    })
  }

  checks.push({
    id: 'worker-redis',
    name: 'Worker / Redis 深度检测',
    path: '/api/diagnostics/worker',
    description: '真实检测 Redis broker、worker-media 在线状态和 media.process_asset 核心照片处理任务是否注册。',
  })

  return checks
}

async function runDiagnostics() {
  diagnosticsRunning.value = true
  diagnosticsMessage.value = '正在执行系统检测……'
  diagnosticsLastRun.value = formatDate(new Date().toISOString())
  diagnosticsResults.value = buildDiagnosticChecks().map((check) => ({
    ...check,
    status: 'running',
    statusText: diagnosticStatusName('running'),
    detail: '等待检测结果……',
    payload: null,
    durationMs: 0,
  }))

  const checks = buildDiagnosticChecks()
  const results = []

  for (const check of checks) {
    const result = await runOneDiagnostic(check)
    results.push(result)
    diagnosticsResults.value = [
      ...results,
      ...checks.slice(results.length).map((item) => ({
        ...item,
        status: 'running',
        statusText: diagnosticStatusName('running'),
        detail: '等待检测结果……',
        payload: null,
        durationMs: 0,
      })),
    ]
  }

  diagnosticsResults.value = results

  const failedCount = results.filter((item) => item.status === 'failed').length
  const warningCount = results.filter((item) => item.status === 'warning').length
  const skippedCount = results.filter((item) => item.status === 'skipped').length
  const okCount = results.filter((item) => item.status === 'ok').length

  diagnosticsMessage.value = `检测完成：正常 ${okCount} 项，警告 ${warningCount} 项，失败 ${failedCount} 项，跳过 ${skippedCount} 项。`
  diagnosticsRunning.value = false
}

watch(isDiagnosticsPage, async (isDiagnostic) => {
  if (isDiagnostic) {
    detachMap()
    return
  }

  await restoreHomeMap()
})

watch(currentProject, async (project) => {
  if (!project?.id) {
    assets.value = []
    return
  }

  await nextTick()
  await loadAssets(project.id)
  await refreshAllTaskData()

  if (activeTaskCount.value > 0) {
    startSmartPolling('当前项目存在等待中或处理中的后台任务，已自动启动智能轮询。')
  }
})

onMounted(async () => {
  syncRoute()
  window.addEventListener('hashchange', syncRoute)
  window.addEventListener('resize', handleWindowResize)
  handleWindowResize()
  initMap()
  await loadProjects()
  await refreshAllTaskData()

  if (activeTaskCount.value > 0) {
    startSmartPolling('检测到已有等待中或处理中的后台任务，已自动启动智能轮询。')
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('hashchange', syncRoute)
  window.removeEventListener('resize', handleWindowResize)
  stopSidebarResize()
  stopTrackedTaskPolling()
  stopSmartPolling()

  if (sidebarResizeFrame) {
    cancelAnimationFrame(sidebarResizeFrame)
    sidebarResizeFrame = null
  }

  if (mapMarkerSource) {
    mapMarkerSource.clear()
  }

  if (manualGpsSource) {
    manualGpsSource.clear()
  }

  if (mapClusterSource) {
    mapClusterSource.clear()
  }

  if (mapInstance) {
    mapInstance.setTarget(null)
    mapInstance = null
  }
})
</script>

<template>
  <div :class="['app-shell', { 'sidebar-is-resizing': sidebarResizing }]">
    <header class="app-header">
      <div class="brand-block">
        <div class="brand-row">
          <h1>工程照片地图管理系统</h1>
          <button class="sidebar-toggle-btn" @click="toggleSidebar">
            {{ sidebarOpen ? '隐藏侧边栏' : '侧边栏' }}
          </button>
        </div>
      </div>

      <div v-if="!isDiagnosticsPage" class="header-search-box" role="search">
        <span class="header-search-icon" aria-hidden="true">⌕</span>
        <input
          v-model="mapSearchKeyword"
          type="text"
          placeholder="搜索照片、项目、道路或标识"
          @keyup.enter="runMapSearch"
        />
        <button class="header-search-btn" @click="runMapSearch">搜索</button>
      </div>

      <nav class="top-nav">
        <button :class="!isDiagnosticsPage ? 'nav-btn active' : 'nav-btn'" @click="navigateTo('/')">首页</button>
        <button :class="isDiagnosticsPage ? 'nav-btn active' : 'nav-btn'" @click="navigateTo('/diagnostics')">系统检测</button>
      </nav>

      <div class="header-actions">
        <button class="header-mini-btn" @click="headerPlaceholder('语言')">语言</button>
        <button class="header-mini-btn" @click="headerPlaceholder('登录')">登录</button>
        <button class="header-mini-btn" @click="headerPlaceholder('注册')">注册</button>
      </div>
    </header>

    <main v-if="!isDiagnosticsPage" class="app-main">
      <section
        v-show="sidebarOpen"
        :class="['left-panel', { 'left-panel-resizing': sidebarResizing }]"
        :style="sidebarStyle"
      >
        <div class="sidebar-close-row">
          <div class="sidebar-window-actions">
            <button
              class="sidebar-size-btn"
              type="button"
              :title="sidebarMaximized ? '还原侧边栏' : '最大化侧边栏'"
              :aria-label="sidebarMaximized ? '还原侧边栏' : '最大化侧边栏'"
              @click="toggleSidebarMaximize"
            >
              <span class="sidebar-maximize-icon" aria-hidden="true"></span>
            </button>
            <button class="sidebar-close-btn" type="button" @click="closeSidebar">×</button>
          </div>
        </div>

        <div class="sidebar-tab-row" role="tablist" aria-label="工作侧边栏标签">
          <button
            v-for="tab in sidebarTabs"
            :key="tab.key"
            type="button"
            :class="['sidebar-tab-button', { active: activeSidebarTab === tab.key }]"
            @click="setSidebarTab(tab.key)"
          >
            {{ tab.name }}
          </button>
        </div>

        <div class="sidebar-tab-content">
          <template v-if="activeSidebarTab === 'project'">
            <div class="card">
              <h2>项目管理</h2>

              <div class="form-group">
                <label>项目名称</label>
                <input v-model="projectForm.name" type="text" placeholder="例如：新华路道路维修工程" />
              </div>

              <div class="form-group">
                <label>项目编号</label>
                <input v-model="projectForm.code" type="text" placeholder="例如：XHL-2026-001" />
              </div>

              <div class="form-group">
                <label>项目说明</label>
                <textarea v-model="projectForm.description" placeholder="可填写项目说明，也可以暂时不填"></textarea>
              </div>

              <div class="button-row">
                <button class="primary-btn" @click="createProject">创建项目</button>
                <button class="secondary-btn" @click="loadProjects">刷新项目列表</button>
              </div>

              <div class="message-box">{{ projectMessage }}</div>

              <h3>项目列表</h3>

              <div v-if="projects.length === 0" class="empty-box">暂无项目</div>

              <div v-for="project in projects" :key="project.id" class="project-item">
                <div>
                  <h4>{{ project.name }}</h4>
                  <p>编号：{{ project.code || project.project_code || '-' }}</p>
                  <p>创建时间：{{ formatDate(project.created_at) }}</p>
                </div>

                <button
                  :class="project.id === currentProject?.id ? 'disabled-btn' : 'primary-btn'"
                  @click="setCurrentProject(project)"
                >
                  {{ project.id === currentProject?.id ? '当前项目' : '设为当前项目' }}
                </button>
              </div>
            </div>
          </template>

          <template v-else-if="activeSidebarTab === 'photos'">
            <div class="card">
              <h2>照片上传与列表</h2>

              <div v-if="currentProject" class="current-upload-box">
                当前上传到：
                <strong>{{ currentProject.name }}</strong>
                （项目 ID：{{ currentProject.id }}）
              </div>

              <div v-else class="empty-box">
                请先在“项目”标签选择一个项目，然后再上传照片。
              </div>

              <div class="upload-box">
                <input ref="fileInputRef" type="file" multiple accept="image/*" @change="handleFileChange" />

                <div class="button-row">
                  <button class="primary-btn" :disabled="uploading" @click="uploadPhotos">
                    {{ uploading ? '上传中……' : '上传照片' }}
                  </button>

                  <button class="secondary-btn" @click="currentProject?.id && loadAssets(currentProject.id)">
                    刷新照片列表
                  </button>
                </div>
              </div>

              <div class="message-box">{{ uploadMessage }}</div>

              <h3>当前项目照片记录</h3>

              <p class="stats-line">
                共 {{ assetStats.total }} 张，
                有 GPS {{ assetStats.gps }} 张，
                无 GPS {{ assetStats.noGps }} 张，
                已处理 {{ assetStats.processed }} 张，
                未处理 {{ assetStats.pending }} 张
              </p>

              <div class="filter-row">
                <button :class="assetFilter === 'all' ? 'active-filter' : 'filter-btn'" @click="setAssetFilter('all')">
                  全部 {{ assetStats.total }}
                </button>
                <button :class="assetFilter === 'gps' ? 'active-filter' : 'filter-btn'" @click="setAssetFilter('gps')">
                  有 GPS {{ assetStats.gps }}
                </button>
                <button :class="assetFilter === 'no_gps' ? 'active-filter' : 'filter-btn'" @click="setAssetFilter('no_gps')">
                  无 GPS {{ assetStats.noGps }}
                </button>
                <button :class="assetFilter === 'processed' ? 'active-filter' : 'filter-btn'" @click="setAssetFilter('processed')">
                  已处理 {{ assetStats.processed }}
                </button>
                <button :class="assetFilter === 'pending' ? 'active-filter' : 'filter-btn'" @click="setAssetFilter('pending')">
                  未处理 {{ assetStats.pending }}
                </button>
              </div>

              <div v-if="filteredAssets.length === 0" class="empty-box">暂无照片记录</div>

              <div
                v-for="asset in filteredAssets"
                :id="assetDomId(asset)"
                :key="asset.id"
                :class="['photo-card', { 'photo-card-selected': isSelectedAsset(asset) }]"
                @click="selectSidebarAsset(asset)"
              >
                <button class="photo-thumb-button" @click.stop="selectSidebarAsset(asset)">
                  <img v-if="assetThumbUrl(asset)" :src="assetThumbUrl(asset)" :alt="assetFilename(asset)" />
                  <span v-else>暂无缩略图</span>
                </button>

                <div class="photo-info">
                  <h3>#{{ asset.id }} {{ assetFilename(asset) }}</h3>

                  <div class="badge-row">
                    <span :class="['badge', assetStatusClass(asset)]">
                      {{ assetStatusText(asset) }}
                    </span>
                    <span :class="['badge', itemHasGps(asset) ? 'badge-success' : 'badge-muted']">
                      GPS：{{ gpsText(asset) }}
                    </span>
                    <span :class="['badge', itemHasGps(asset) ? 'badge-success' : 'badge-muted']">
                      来源：{{ gpsSourceText(asset) }}
                    </span>
                    <span :class="['badge', asset.shot_at ? 'badge-success' : 'badge-muted']">
                      拍摄时间：{{ shotTimeText(asset) }}
                    </span>
                  </div>

                  <p><strong>拍摄时间：</strong>{{ formatDate(asset.shot_at) }}</p>
                  <p><strong>创建时间：</strong>{{ formatDate(asset.created_at) }}</p>
                  <p><strong>GPS 来源：</strong>{{ gpsSourceText(asset) }}</p>
                  <p><strong>GPS 状态：</strong>{{ gpsStatusText(asset) }}</p>
                  <p><strong>GPS 坐标：</strong>{{ assetCoordinateText(asset) }}</p>

                  <div class="button-row">
                    <button class="primary-btn small-btn" @click.stop="showPreview(asset)">查看预览</button>
                    <button class="light-btn small-btn" @click.stop="openMedia(assetOriginalUrl(asset))">打开原图</button>
                    <button class="light-btn small-btn" :disabled="!itemHasGps(asset)" @click.stop="focusMapOnAsset(asset)">定位点位</button>
                  </div>

                  <button class="dark-btn small-btn" @click.stop="toggleAssetDetail(asset.id)">
                    {{ isAssetExpanded(asset.id) ? '收起详情' : '展开详情' }}
                  </button>

                  <div v-if="isAssetExpanded(asset.id)" class="detail-box">
                    <p><strong>asset id：</strong>{{ asset.id }}</p>
                    <p><strong>project id：</strong>{{ asset.project_id }}</p>
                    <p><strong>latitude：</strong>{{ asset.latitude ?? '-' }}</p>
                    <p><strong>longitude：</strong>{{ asset.longitude ?? '-' }}</p>
                    <p><strong>GPS 来源：</strong>{{ gpsSourceText(asset) }}</p>
                    <p><strong>GPS 状态：</strong>{{ gpsStatusText(asset) }}</p>
                    <p><strong>gps_source：</strong>{{ asset.gps_source || '-' }}</p>
                    <p><strong>gps_status：</strong>{{ asset.gps_status || '-' }}</p>
                    <p><strong>storage_path：</strong>{{ asset.storage_path || '-' }}</p>
                    <p><strong>thumb_path：</strong>{{ asset.thumb_path || '-' }}</p>
                    <p><strong>preview_path：</strong>{{ asset.preview_path || '-' }}</p>
                    <p><strong>original_url：</strong>{{ asset.original_url || '-' }}</p>
                    <p><strong>thumb_url：</strong>{{ asset.thumb_url || '-' }}</p>
                    <p><strong>preview_url：</strong>{{ asset.preview_url || '-' }}</p>
                    <p><strong>updated_at：</strong>{{ formatDate(asset.updated_at) }}</p>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="activeSidebarTab === 'noGps'">
            <div class="card">
              <h2>无 GPS 照片</h2>
              <p class="stats-line">
                当前项目共 {{ assetStats.noGps }} 张无 GPS 照片。先选照片，再在地图上点击位置，确认后保存到数据库。
              </p>

              <div class="button-row">
                <button class="primary-btn small-btn" @click="setSidebarTab('photos'); setAssetFilter('no_gps')">在照片页筛选无 GPS</button>
                <button class="secondary-btn small-btn" @click="currentProject?.id && loadAssets(currentProject.id)">刷新照片</button>
              </div>

              <div v-if="manualGpsAsset" class="manual-gps-panel">
                <div class="manual-gps-panel-header">
                  <div>
                    <h3>正在补点</h3>
                    <p>#{{ manualGpsAsset.id }} {{ assetFilename(manualGpsAsset) }}</p>
                  </div>
                  <button class="light-btn small-btn" @click="cancelManualGps()">取消</button>
                </div>

                <div class="manual-gps-body">
                  <button class="manual-gps-thumb" @click="showPreview(manualGpsAsset)">
                    <img v-if="assetThumbUrl(manualGpsAsset)" :src="assetThumbUrl(manualGpsAsset)" :alt="assetFilename(manualGpsAsset)" />
                    <span v-else>暂无缩略图</span>
                  </button>
                  <div class="manual-gps-text">
                    <p>1. 在地图上点击照片实际位置。</p>
                    <p>2. 橙色临时指针出现后，点击“保存补点”。</p>
                    <p>3. 保存后这张照片会从无 GPS 列表移到地图点位。</p>
                  </div>
                </div>

                <div class="manual-gps-coordinate-grid">
                  <div>
                    <span>纬度 latitude</span>
                    <strong>{{ manualGpsDraft ? manualGpsDraft.latitude.toFixed(6) : '-' }}</strong>
                  </div>
                  <div>
                    <span>经度 longitude</span>
                    <strong>{{ manualGpsDraft ? manualGpsDraft.longitude.toFixed(6) : '-' }}</strong>
                  </div>
                </div>

                <div class="button-row">
                  <button class="light-btn small-btn" @click="useMapCenterForManualGps">取地图中心</button>
                  <button class="primary-btn small-btn" :disabled="manualGpsSaving || !manualGpsDraft" @click="saveManualGps">
                    {{ manualGpsSaving ? '保存中……' : '保存补点' }}
                  </button>
                </div>

                <div class="message-box">{{ manualGpsMessage }}</div>
              </div>

              <div v-if="!currentProject" class="empty-box">请先在“项目”标签选择当前项目。</div>
              <div v-else-if="noGpsAssets.length === 0" class="empty-box">当前项目没有无 GPS 照片。</div>

              <div v-for="asset in noGpsAssets" :key="`nogps-${asset.id}`" class="sidebar-mini-photo">
                <button class="sidebar-mini-thumb" @click="showPreview(asset)">
                  <img v-if="assetThumbUrl(asset)" :src="assetThumbUrl(asset)" :alt="assetFilename(asset)" />
                  <span v-else>暂无缩略图</span>
                </button>
                <div class="sidebar-mini-info">
                  <strong>#{{ asset.id }} {{ assetFilename(asset) }}</strong>
                  <span>拍摄：{{ formatDate(asset.shot_at) }}</span>
                  <span>状态：{{ assetStatusText(asset) }}</span>
                  <div class="button-row sidebar-mini-actions">
                    <button class="primary-btn small-btn" @click="showPreview(asset)">预览</button>
                    <button :class="manualGpsAsset?.id === asset.id ? 'primary-btn small-btn' : 'light-btn small-btn'" @click="startManualGps(asset)">{{ manualGpsAsset?.id === asset.id ? '正在补点' : '补点' }}</button>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="activeSidebarTab === 'points'">
            <div class="card">
              <h2>地图点位</h2>
              <div class="sidebar-stat-grid">
                <div class="sidebar-stat-card">
                  <span>有效 GPS</span>
                  <strong>{{ mapPointStats.valid }}</strong>
                </div>
                <div class="sidebar-stat-card">
                  <span>无效/缺失</span>
                  <strong>{{ mapPointStats.invalid }}</strong>
                </div>
                <div class="sidebar-stat-card">
                  <span>聚合组</span>
                  <strong>{{ visibleClusterStats.clusterGroups }}</strong>
                </div>
                <div class="sidebar-stat-card">
                  <span>重合组</span>
                  <strong>{{ mapGroupStats.overlapGroups }}</strong>
                </div>
              </div>

              <div class="message-box">{{ mapAssetsMessage }}</div>

              <div class="button-row">
                <button class="primary-btn small-btn" :disabled="mapAssetsLoading || !currentProjectId" @click="currentProjectId && loadMapAssets(currentProjectId, { fit: true })">
                  {{ mapAssetsLoading ? '刷新中……' : '刷新并缩放到点位' }}
                </button>
                <button class="light-btn small-btn" :disabled="gpsAssets.length === 0" @click="setSidebarTab('photos'); setAssetFilter('gps')">查看 GPS 照片</button>
              </div>

              <p class="sidebar-help-text">
                地图上继续使用右侧工具栏和动态聚合点位；这个标签只做点位统计和快速入口。
              </p>
            </div>
          </template>

          <template v-else-if="activeSidebarTab === 'tasks'">
            <div class="card">
              <div class="section-title-row">
                <div>
                  <h2>任务状态中心</h2>
                  <p>查看照片上传后的 worker 后台处理任务，便于确认缩略图、预览图、EXIF/GPS 是否处理完成。</p>
                </div>

                <button class="light-btn small-btn" @click="refreshAllTaskData">手动刷新</button>
              </div>

              <div class="task-summary-grid">
                <button class="summary-card" @click="setTaskStatusFilter('all')">
                  <span>全部</span>
                  <strong>{{ taskStats.total }}</strong>
                </button>
                <button class="summary-card" @click="setTaskStatusFilter('pending')">
                  <span>等待中</span>
                  <strong>{{ taskStats.pending }}</strong>
                </button>
                <button class="summary-card warning" @click="setTaskStatusFilter('processing')">
                  <span>处理中</span>
                  <strong>{{ taskStats.processing }}</strong>
                </button>
                <button class="summary-card success" @click="setTaskStatusFilter('done')">
                  <span>已完成</span>
                  <strong>{{ taskStats.done }}</strong>
                </button>
                <button class="summary-card danger" @click="setTaskStatusFilter('failed')">
                  <span>失败</span>
                  <strong>{{ taskStats.failed }}</strong>
                </button>
              </div>

              <div class="filter-row">
                <button :class="taskScope === 'current' ? 'active-filter' : 'filter-btn'" @click="setTaskScope('current')">
                  当前项目
                </button>
                <button :class="taskScope === 'all' ? 'active-filter' : 'filter-btn'" @click="setTaskScope('all')">
                  全部项目
                </button>
              </div>

              <div class="filter-row">
                <button :class="taskStatusFilter === 'all' ? 'active-filter' : 'filter-btn'" @click="setTaskStatusFilter('all')">
                  全部
                </button>
                <button :class="taskStatusFilter === 'pending' ? 'active-filter' : 'filter-btn'" @click="setTaskStatusFilter('pending')">
                  等待中
                </button>
                <button :class="taskStatusFilter === 'processing' ? 'active-filter' : 'filter-btn'" @click="setTaskStatusFilter('processing')">
                  处理中
                </button>
                <button :class="taskStatusFilter === 'done' ? 'active-filter' : 'filter-btn'" @click="setTaskStatusFilter('done')">
                  已完成
                </button>
                <button :class="taskStatusFilter === 'failed' ? 'active-filter' : 'filter-btn'" @click="setTaskStatusFilter('failed')">
                  失败
                </button>
              </div>

              <div class="button-row">
                <button class="primary-btn" @click="refreshAllTaskData">刷新任务状态</button>
              </div>

              <div class="message-box">{{ taskMessage }}</div>

              <div class="task-tracking-message">
                <strong>智能轮询：</strong>{{ smartPollingRunning ? '运行中' : '空闲' }}
                <span v-if="smartPollingLastRefresh">；最近刷新：{{ smartPollingLastRefresh }}</span>
                <br />
                {{ smartPollingMessage }}
              </div>

              <div v-if="trackedTaskMessage" class="task-tracking-message">
                {{ trackedTaskMessage }}
              </div>

              <div v-if="trackedTask" class="task-tracking-box">
                <div>
                  <strong>当前追踪任务：</strong>
                  #{{ trackedTask.id }} / {{ taskStatusName(trackedTask.status) }} / {{ trackedTask.progress ?? 0 }}%
                </div>

                <div v-if="taskFilename(trackedTask)">
                  <strong>文件：</strong>
                  {{ taskFilename(trackedTask) }}
                </div>

                <div v-if="shouldShowTaskError(trackedTask)" class="task-error-message">
                  <strong>错误：</strong>
                  {{ taskErrorText(trackedTask) }}
                </div>
              </div>

              <div v-if="failedTasks.length > 0" class="failed-task-summary">
                <h3>发现失败任务：{{ failedTasks.length }} 条</h3>
                <p>以下任务需要优先排查。可以点击“失败”筛选按钮，只查看失败任务。</p>
                <ul>
                  <li v-for="task in failedTasks" :key="`failed-${task.id}`">
                    <strong>#{{ task.id }}</strong>
                    {{ taskFileDisplay(task) }}：{{ taskErrorText(task) }}
                  </li>
                </ul>
              </div>

              <div v-if="taskScope === 'current' && !currentProject" class="empty-box">
                当前范围为“当前项目”，请先选择一个项目；或者切换到“全部项目”。
              </div>

              <div
                v-for="task in tasks"
                :key="task.id"
                class="task-card"
                :class="{ 'task-card-failed': shouldShowTaskError(task) }"
              >
                <div class="task-card-header">
                  <h3>#{{ task.id }} {{ taskFilename(task) }}</h3>
                  <span :class="['badge', taskStatusClass(task.status)]">
                    {{ taskStatusName(task.status) }}
                  </span>
                </div>

                <div class="progress-row">
                  <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: `${task.progress ?? 0}%` }"></div>
                  </div>
                  <span>{{ task.progress ?? 0 }}%</span>
                </div>

                <div class="task-meta-grid">
                  <p><strong>类型：</strong>{{ task.type || '-' }}</p>
                  <p><strong>项目 ID：</strong>{{ taskProjectId(task) }}</p>
                  <p><strong>照片 ID：</strong>{{ taskAssetId(task) }}</p>
                  <p><strong>创建时间：</strong>{{ formatDate(task.created_at) }}</p>
                  <p><strong>完成时间：</strong>{{ formatDate(task.finished_at) }}</p>
                  <p><strong>celery_task_id：</strong>{{ task.celery_task_id || '-' }}</p>
                </div>

                <div v-if="shouldShowTaskError(task)" class="task-error-panel">
                  <div class="task-error-title">
                    <strong>任务失败 / 异常信息</strong>
                  </div>
                  <p><strong>文件：</strong>{{ taskFileDisplay(task) }}</p>
                  <p><strong>项目 ID：</strong>{{ taskProjectId(task) }}</p>
                  <p><strong>照片 ID：</strong>{{ taskAssetId(task) }}</p>
                  <p><strong>错误原因：</strong>{{ taskErrorText(task) }}</p>
                  <p><strong>建议处理：</strong>{{ taskFailureAdvice(task) }}</p>
                </div>

                <button class="dark-btn small-btn" @click="toggleAssetDetail(`task-${task.id}`)">
                  {{ isAssetExpanded(`task-${task.id}`) ? '收起详情' : '展开详情' }}
                </button>

                <div v-if="isAssetExpanded(`task-${task.id}`)" class="detail-box">
                  <p><strong>payload_json：</strong></p>
                  <pre>{{ safeJson(task.payload_json) }}</pre>

                  <p><strong>result_json：</strong></p>
                  <pre>{{ safeJson(task.result_json) }}</pre>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="activeSidebarTab === 'export'">
            <div class="card">
              <h2>导出、打印与工具</h2>
              <p class="sidebar-help-text">
                当前版本整理 QGIS 导出、地图打印和照片清单打印三个入口；打印资料包当前为说明面板，后续版本再升级为正式 PDF / ZIP 打包。
              </p>

              <div class="export-summary-box">
                <p><strong>当前项目：</strong>{{ currentProjectName }}</p>
                <p><strong>可导出点位：</strong>{{ mapPointStats.valid }} 个有效 GPS 点位</p>
                <p><strong>导出范围：</strong>当前项目内有 latitude / longitude 的照片。</p>
                <p><strong>文件命名：</strong>项目名称_点位导出_日期时间；QGIS 样式、说明和资料包分别为 项目名称_QGIS样式_日期时间、项目名称_QGIS使用说明_日期时间、项目名称_QGIS资料包_日期时间。</p>
              </div>

              <div class="export-panel-section">
                <h3>QGIS 数据导出</h3>
                <div class="sidebar-action-list">
                  <button class="light-btn" :disabled="!currentProjectId || exportRunning || mapPointStats.valid < 1" @click="downloadCurrentProjectCsv">{{ exportRunning ? '导出中……' : '导出 CSV 点位表' }}</button>
                  <button class="light-btn" :disabled="!currentProjectId || exportRunning || mapPointStats.valid < 1" @click="downloadCurrentProjectGeoJson">{{ exportRunning ? '导出中……' : '导出 GeoJSON / QGIS 图层' }}</button>
                  <button class="light-btn" :disabled="!currentProjectId || exportRunning" @click="downloadCurrentProjectQgisStyle">{{ exportRunning ? '导出中……' : '导出 QGIS 样式 QML' }}</button>
                  <button class="light-btn" :disabled="!currentProjectId || exportRunning" @click="downloadCurrentProjectQgisReadme">{{ exportRunning ? '导出中……' : '导出 QGIS 使用说明 TXT' }}</button>
                  <button class="primary-btn" :disabled="!currentProjectId || exportRunning || mapPointStats.valid < 1" @click="downloadCurrentProjectQgisPackage">{{ exportRunning ? '打包中……' : '一键导出 QGIS 资料包 ZIP' }}</button>
                </div>
              </div>

              <div class="print-panel-card">
                <div class="print-panel-title">
                  <h3>打印出图入口</h3>
                  <span>V0.3.27 文字收口</span>
                </div>
                <p class="sidebar-help-text">
                  本版保留已跑通的地图打印和照片清单打印，并把打印资料包入口整理为阶段说明面板。
                </p>
                <div class="print-summary-grid">
                  <div class="sidebar-stat-card">
                    <span>照片总数</span>
                    <strong>{{ assetStats.total }}</strong>
                  </div>
                  <div class="sidebar-stat-card">
                    <span>GPS 照片</span>
                    <strong>{{ assetStats.gps }}</strong>
                  </div>
                  <div class="sidebar-stat-card">
                    <span>无 GPS</span>
                    <strong>{{ assetStats.noGps }}</strong>
                  </div>
                  <div class="sidebar-stat-card">
                    <span>地图点位</span>
                    <strong>{{ mapPointStats.valid }}</strong>
                  </div>
                </div>

                <div class="print-options-box">
                  <h4>地图打印参数</h4>
                  <div class="print-options-grid">
                    <label class="print-option-row">
                      <span>纸张大小</span>
                      <select v-model="printMapOptions.paperSize">
                        <option value="A4">A4</option>
                        <option value="A3">A3</option>
                      </select>
                    </label>
                    <label class="print-option-row">
                      <span>打印方向</span>
                      <select v-model="printMapOptions.orientation">
                        <option value="landscape">横向</option>
                        <option value="portrait">纵向</option>
                      </select>
                    </label>
                    <label class="print-option-row">
                      <span>打印质量</span>
                      <select v-model="printMapOptions.quality">
                        <option value="small">小体积</option>
                        <option value="standard">标准</option>
                        <option value="high">高清</option>
                      </select>
                    </label>
                    <label class="print-option-row">
                      <span>打印范围</span>
                      <select v-model="printMapOptions.range">
                        <option value="current_project">当前项目全部点位</option>
                        <option value="current_view">当前地图视野</option>
                      </select>
                    </label>
                  </div>
                  <div class="print-checkbox-grid">
                    <label><input v-model="printMapOptions.showTitle" type="checkbox"> 显示标题</label>
                    <label><input v-model="printMapOptions.showScale" type="checkbox"> 显示比例尺</label>
                    <label><input v-model="printMapOptions.showNorth" type="checkbox"> 显示指北针</label>
                    <label><input v-model="printMapOptions.showPointNumber" type="checkbox"> 显示点位编号</label>
                  </div>
                  <p class="print-option-summary">当前地图参数：{{ printMapOptionText }}</p>
                </div>

                <div class="print-options-box compact">
                  <h4>照片清单参数</h4>
                  <div class="print-options-grid">
                    <label class="print-option-row">
                      <span>纸张大小</span>
                      <select v-model="printPhotoOptions.paperSize">
                        <option value="A4">A4</option>
                        <option value="A3">A3</option>
                      </select>
                    </label>
                    <label class="print-option-row">
                      <span>打印方向</span>
                      <select v-model="printPhotoOptions.orientation">
                        <option value="portrait">纵向</option>
                        <option value="landscape">横向</option>
                      </select>
                    </label>
                    <label class="print-option-row">
                      <span>照片版式</span>
                      <select v-model="printPhotoOptions.layout">
                        <option v-for="option in printPhotoLayoutOptions" :key="option.value" :value="option.value">{{ option.name }}</option>
                      </select>
                    </label>
                  </div>
                  <div class="print-checkbox-grid two-col">
                    <label><input v-model="printPhotoOptions.includeInfo" type="checkbox"> 显示照片信息</label>
                    <label><input v-model="printPhotoOptions.includePageNo" type="checkbox"> 显示页码</label>
                  </div>
                  <p class="print-option-summary">当前照片参数：{{ printPhotoOptionText }}</p>
                </div>

                <div class="sidebar-action-list">
                  <button class="light-btn" :disabled="!currentProjectId || mapPointStats.valid < 1 || printMapPreviewLoading" @click="openPrintMapPreview">{{ printMapPreviewLoading ? '生成预览中...' : '打印地图预览' }}</button>
                  <button class="light-btn" :disabled="!currentProjectId || assetStats.total < 1" @click="openPrintPhotoListPreview">打印照片清单预览</button>
                  <button class="light-btn" :disabled="!currentProjectId" @click="showPrintPackageEntryMessage">打印资料包说明</button>
                </div>
              </div>

              <div class="sidebar-action-list">
                <button class="primary-btn" @click="navigateTo('/diagnostics')">打开系统检测</button>
              </div>

              <div class="empty-box">
                QGIS 使用建议：正式留档时优先使用“一键导出 QGIS 资料包 ZIP”；打印出图当前已支持地图预览、照片清单预览和打印资料包说明。正式 PDF 与 ZIP 后续版本再增强。
              </div>
            </div>
          </template>
        </div>

        <div
          class="sidebar-resize-handle"
          role="separator"
          aria-label="拖动调整侧边栏宽度"
          aria-orientation="vertical"
          @pointerdown="startSidebarResize"
        ></div>
      </section>

      <section class="right-panel" :style="rightPanelStyle">
        <div class="map-card">
          <div class="map-shell">
            <div class="osm-map-toolbar" aria-label="地图工具栏">
              <button aria-label="放大" data-tooltip="放大" @click="zoomMapIn">＋</button>
              <button aria-label="缩小" data-tooltip="缩小" @click="zoomMapOut">－</button>
              <button aria-label="我的位置" data-tooltip="我的位置" @click="locateCurrentPosition">⌖</button>
              <button aria-label="刷新点位" data-tooltip="刷新点位" :disabled="mapAssetsLoading || !currentProjectId" @click="currentProjectId && loadMapAssets(currentProjectId, { fit: true })">
                {{ mapAssetsLoading ? '…' : '↻' }}
              </button>
              <button aria-label="图层" data-tooltip="图层" @click="toggleMapPanel('layers')">▰</button>
              <button aria-label="图例" data-tooltip="图例" @click="toggleMapPanel('legend')">i</button>
              <button aria-label="分享" data-tooltip="分享" @click="toggleMapPanel('share')">↗</button>
              <button aria-label="现场注记" data-tooltip="现场注记" @click="toggleMapPanel('note')">☰</button>
              <button aria-label="地图帮助" data-tooltip="地图帮助" @click="toggleMapPanel('help')">?</button>
            </div>

            <div v-if="mapUiPanel" class="osm-side-drawer">
              <div class="osm-side-drawer-header">
                <h3 v-if="mapUiPanel === 'layers'">地图图层</h3>
                <h3 v-else-if="mapUiPanel === 'legend'">图例</h3>
                <h3 v-else-if="mapUiPanel === 'share'">分享</h3>
                <h3 v-else-if="mapUiPanel === 'note'">现场注记</h3>
                <h3 v-else-if="mapUiPanel === 'help'">地图帮助</h3>
                <h3 v-else>提示</h3>
                <button @click="closeMapPanel">×</button>
              </div>

              <div v-if="mapUiPanel === 'layers'" class="osm-panel-body">
                <button
                  v-for="item in basemapOptions"
                  :key="item.key"
                  :class="['osm-layer-option', { active: activeBasemap === item.key }]"
                  @click="setBasemap(item.key)"
                >
                  <strong>{{ item.name }}</strong>
                  <span>{{ item.note }}</span>
                </button>
              </div>

              <div v-else-if="mapUiPanel === 'legend'" class="osm-panel-body legend-list">
                <p><span class="legend-pin blue"></span>普通照片点位</p>
                <p><span class="legend-pin orange"></span>手工补点临时点（未保存）</p>
                <p><span class="legend-pin numbered">3</span>聚合点位 / 重合点位</p>
                <p class="panel-muted">后续版本可继续增加道路、管网、井盖、施工范围等图层图例。</p>
              </div>

              <div v-else-if="mapUiPanel === 'share'" class="osm-panel-body">
                <p>分享入口暂未接入。</p>
                <input class="osm-share-input" :value="currentPageUrl" readonly />
                <p class="panel-muted">后续版本可生成项目地图链接、图片导出、PDF 打印入口。</p>
              </div>

              <div v-else-if="mapUiPanel === 'note'" class="osm-panel-body">
                <p>现场注记入口暂未接入。</p>
                <textarea class="osm-note-input" placeholder="后续版本可在这里记录地图问题、照片说明或现场备注。"></textarea>
                <button class="primary-btn small-btn" @click="showPlaceholderMessage('注记保存功能将在后续版本接入数据库。')">添加注记</button>
              </div>

              <div v-else-if="mapUiPanel === 'help'" class="osm-panel-body">
                <p>地图对象查询暂未接入。</p>
                <p class="panel-muted">后续版本点击地图对象时，可显示照片、道路、井盖、施工范围等属性。</p>
              </div>

              <div v-else class="osm-panel-body">
                <p>{{ mapUiMessage }}</p>
              </div>
            </div>

            <div ref="mapTarget" class="map-container"></div>
          </div>
        </div>
      </section>
    </main>

    <main v-else class="diagnostics-main">
      <section class="diagnostics-card">
        <div class="diagnostics-header">
          <div>
            <p class="diagnostics-kicker">V0.3.20 打印地图预览窗口版</p>
            <h2>系统检测中心</h2>
            <p>
              这里专门用于开发和部署排错，集中检测 API、数据库、项目、任务、照片接口等基础连通性。
            </p>
          </div>

          <div class="diagnostics-actions">
            <button class="primary-btn" :disabled="diagnosticsRunning" @click="runDiagnostics">
              {{ diagnosticsRunning ? '检测中……' : '一键检测' }}
            </button>
            <button class="secondary-btn" @click="navigateTo('/')">返回首页</button>
          </div>
        </div>

        <div class="diagnostics-info-row">
          <div class="diagnostics-message">
            <strong>检测结果：</strong>{{ diagnosticsMessage }}
          </div>
          <div v-if="diagnosticsLastRun" class="diagnostics-time">
            最近检测：{{ diagnosticsLastRun }}
          </div>
        </div>

        <div v-if="diagnosticsResults.length === 0" class="empty-box">
          尚未执行检测。点击“一键检测”后，会依次检查后端 API 和关键业务接口。
        </div>

        <div v-else class="diagnostics-list">
          <div
            v-for="item in diagnosticsResults"
            :key="item.id"
            class="diagnostic-item"
            :class="diagnosticBadgeClass(item.status)"
          >
            <div class="diagnostic-main">
              <div>
                <h3>{{ item.name }}</h3>
                <p>{{ item.description }}</p>
              </div>
              <span class="diagnostic-badge">{{ item.statusText }}</span>
            </div>

            <div class="diagnostic-meta">
              <span><strong>接口：</strong>{{ item.path }}</span>
              <span><strong>耗时：</strong>{{ item.durationMs }} ms</span>
            </div>

            <div class="diagnostic-detail">
              {{ item.detail }}
            </div>

            <details v-if="item.payload" class="diagnostic-payload">
              <summary>查看返回内容</summary>
              <pre>{{ safeJson(item.payload) }}</pre>
            </details>
          </div>
        </div>

        <div class="diagnostics-note">
          <h3>说明</h3>
          <p>
            这一版用于开发阶段的前端接口检测；主界面已经完成项目、照片、GPS、导出和打印等本机闭环能力。
          </p>
          <p>
            当前检测页采用 Hash 路由，访问地址是 <code>http://localhost:5173/#/diagnostics</code>，这样不会影响后续版本 Docker 部署。
          </p>
        </div>
      </section>
    </main>

    <div v-if="printMapPreview.open" class="preview-mask" @click.self="closePrintMapPreview">
      <div class="print-preview-modal">
        <div class="preview-header">
          <div>
            <h2>地图打印预览</h2>
            <p>{{ printMapPreview.title }} · {{ printMapPreview.createdAt }}</p>
          </div>

          <button class="close-btn" @click="closePrintMapPreview">×</button>
        </div>

        <div class="print-preview-body">
          <div :class="printMapPreviewPaperClass">
            <h3 v-if="printMapOptions.showTitle" class="print-preview-title">{{ printMapPreview.title }}</h3>
            <div class="print-preview-subtitle print-map-header-meta">
              <span>项目名称：{{ currentProjectName }}</span>
              <span>点位数量：{{ printMapPreview.pointCount }} 个</span>
              <span>生成时间：{{ printMapPreview.createdAt }}</span>
              <span>纸张：{{ printMapPreview.paperSize }} {{ printMapPreview.orientation === 'landscape' ? '横向' : '纵向' }}</span>
            </div>
            <div class="print-preview-map-frame">
              <img :src="printMapPreview.imageUrl" alt="地图打印预览" />
              <div v-if="printMapOptions.showNorth" class="print-preview-north">
                <span>↑</span>
                <strong>N</strong>
              </div>
              <div v-if="printMapOptions.showScale" class="print-preview-scale">
                <div class="print-preview-scale-line" :style="{ width: `${printMapPreview.scaleBarWidth || 120}px` }"></div>
                <span>{{ printMapPreview.scaleText }}</span>
              </div>
            </div>
            <div class="print-preview-legend">
              <span><strong>图例：</strong>蓝色编号点为当前项目照片 GPS 点位，编号对应照片清单。</span>
              <span>显示元素：{{ printMapElementText }}</span>
            </div>
            <div class="print-preview-meta">
              <span>工程照片地图管理系统 V{{ APP_VERSION }}</span>
              <span>{{ printMapPreview.optionsText }}</span>
            </div>
          </div>
        </div>

        <div class="preview-info">
          <p><strong>说明：</strong>本版保留地图打印标题、项目信息、米制比例尺、指北针、图例和页脚；当前采用浏览器打印，正式 PDF 后续版本再增强。</p>
          <p><strong>当前参数：</strong>{{ printMapPreview.optionsText }}</p>
        </div>

        <div class="preview-footer">
          <button class="light-btn" @click="printMapPreviewByBrowser">调用浏览器打印</button>
          <button class="dark-btn" @click="closePrintMapPreview">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="printPhotoPreview.open" class="preview-mask" @click.self="closePrintPhotoPreview">
      <div class="print-photo-preview-modal">
        <div class="preview-header">
          <div>
            <h2>照片清单预览</h2>
            <p>{{ printPhotoPreview.title }} · {{ printPhotoPreview.createdAt }}</p>
          </div>

          <button class="close-btn" @click="closePrintPhotoPreview">×</button>
        </div>

        <div class="print-photo-preview-body">
          <div
            v-for="(page, pageIndex) in printPhotoPreview.pages"
            :key="`print-photo-page-${pageIndex}`"
            :class="printPhotoPreviewPaperClass"
          >
            <h3 class="print-preview-title">{{ printPhotoPreview.title }}</h3>
            <div class="print-preview-subtitle print-photo-header-meta">
              <span>项目名称：{{ currentProjectName }}</span>
              <span>照片总数：{{ printPhotoPreview.totalCount }} 张</span>
              <span>生成时间：{{ printPhotoPreview.createdAt }}</span>
              <span>版式：{{ printPhotoPreview.paperSize }} · {{ printPhotoPreview.orientation === 'landscape' ? '横向' : '纵向' }} · {{ printPhotoPreview.layout }}</span>
            </div>

            <div :class="printPhotoGridClass(printPhotoPreview.layout)" :style="printPhotoGridStyle(printPhotoPreview.layout)">
              <article v-for="(asset, itemIndex) in page" :key="asset.id" class="print-photo-card">
                <div class="print-photo-image">
                  <img v-if="assetPreviewUrl(asset)" :src="assetPreviewUrl(asset)" :alt="assetFilename(asset)" />
                  <div v-else class="print-photo-empty">暂无图片</div>
                </div>
                <div v-if="printPhotoPreview.includeInfo" class="print-photo-meta">
                  <p><strong>编号：</strong>{{ assetPrintNo(asset, pageIndex * printPhotoPerPage(printPhotoPreview.layout) + itemIndex) }}</p>
                  <p><strong>文件名：</strong>{{ assetFilename(asset) }}</p>
                  <p><strong>拍摄时间：</strong>{{ formatPrintDate(asset.shot_at) }}</p>
                  <p><strong>GPS：</strong>{{ gpsText(asset) }}　<strong>来源：</strong>{{ assetPrintSourceText(asset) }}</p>
                  <p><strong>坐标：</strong>{{ assetPrintCoordinateText(asset) }}</p>
                  <p><strong>GPS 状态：</strong>{{ assetPrintGpsStatusText(asset) }}　<strong>处理：</strong>{{ assetPrintStatusText(asset) }}</p>
                </div>
              </article>
            </div>

            <div v-if="printPhotoPreview.includePageNo" class="print-photo-page-no">
              第 {{ pageIndex + 1 }} 页 / 共 {{ printPhotoPreview.pages.length }} 页
            </div>
          </div>
        </div>

        <div class="preview-info">
          <p><strong>说明：</strong>本版保留照片清单标题、生成时间、照片编号、文件名、拍摄时间、GPS 来源、坐标和处理状态；正式 PDF、照片水印和资料包后续版本再增强。</p>
          <p><strong>当前参数：</strong>{{ printPhotoPreview.optionsText }}</p>
        </div>

        <div class="preview-footer">
          <button class="light-btn" @click="printPhotoPreviewByBrowser">调用浏览器打印</button>
          <button class="dark-btn" @click="closePrintPhotoPreview">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="printPackagePreview.open" class="preview-mask" @click.self="closePrintPackagePreview">
      <div class="print-package-modal">
        <div class="preview-header">
          <div>
            <h2>打印资料包说明</h2>
            <p>{{ printPackagePreview.title }} · {{ printPackagePreview.createdAt }}</p>
          </div>

          <button class="close-btn" @click="closePrintPackagePreview">×</button>
        </div>

        <div class="print-package-body">
          <section class="print-package-card">
            <h3>当前项目统计</h3>
            <div class="print-package-stats">
              <div>
                <span>照片总数</span>
                <strong>{{ printPackagePreview.totalPhotos }}</strong>
              </div>
              <div>
                <span>GPS 照片</span>
                <strong>{{ printPackagePreview.gpsPhotos }}</strong>
              </div>
              <div>
                <span>无 GPS</span>
                <strong>{{ printPackagePreview.noGpsPhotos }}</strong>
              </div>
              <div>
                <span>地图点位</span>
                <strong>{{ printPackagePreview.mapPoints }}</strong>
              </div>
            </div>
          </section>

          <section class="print-package-card">
            <h3>当前可用打印内容</h3>
            <ul class="print-package-list">
              <li v-for="item in printPackagePreview.packageFiles" :key="item">{{ item }}</li>
            </ul>
          </section>

          <section class="print-package-card">
            <h3>当前打印参数</h3>
            <p><strong>地图：</strong>{{ printPackagePreview.mapOptionsText }}</p>
            <p><strong>照片清单：</strong>{{ printPackagePreview.photoOptionsText }}</p>
          </section>

          <section class="print-package-card">
            <h3>后续正式资料包目标</h3>
            <ul class="print-package-list">
              <li v-for="item in printPackagePreview.nextSteps" :key="item">{{ item }}</li>
            </ul>
          </section>
        </div>

        <div class="preview-info">
          <p><strong>说明：</strong>本版先把打印资料包说明和内容清单整理清楚，不生成后端 PDF 或 ZIP，避免影响已经跑通的地图打印、照片清单打印和 QGIS 导出。</p>
        </div>

        <div class="preview-footer">
          <button class="light-btn" :disabled="mapPointStats.valid < 1" @click="openPrintMapPreview">打开地图打印预览</button>
          <button class="light-btn" :disabled="assetStats.total < 1" @click="openPrintPhotoListPreview">打开照片清单预览</button>
          <button class="dark-btn" @click="closePrintPackagePreview">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="mapPointGroupAssets.length > 1" class="preview-mask" @click.self="closeMapPointGroup">
      <div class="map-point-group-modal">
        <div class="preview-header">
          <div>
            <h2>重合点位照片</h2>
            <p>当前位置共有 {{ mapPointGroupAssets.length }} 张 GPS 坐标相同或极接近的照片。</p>
          </div>

          <button class="close-btn" @click="closeMapPointGroup">×</button>
        </div>

        <div class="map-point-group-list">
          <div
            v-for="asset in mapPointGroupAssets"
            :key="asset.id"
            :class="['map-point-group-item', { 'map-point-group-item-selected': isSelectedAsset(asset) }]"
          >
            <img v-if="assetThumbUrl(asset)" :src="assetThumbUrl(asset)" :alt="assetFilename(asset)" />
            <div v-else class="map-point-group-thumb-empty">暂无缩略图</div>
            <div class="map-point-group-info">
              <strong>{{ assetFilename(asset) }}</strong>
              <span>#{{ asset.id }} · {{ formatDate(asset.shot_at) }}</span>
              <span>GPS 来源：{{ gpsSourceText(asset) }}</span>
              <span>GPS 状态：{{ gpsStatusText(asset) }}</span>
              <span>GPS 坐标：{{ assetCoordinateText(asset) }}</span>
              <div class="map-point-group-actions">
                <button class="primary-btn small-btn" @click="openMapPointGroupAsset(asset)">查看预览</button>
                <button class="light-btn small-btn" @click="locateMapPointFromGroup(asset)">定位列表</button>
              </div>
            </div>
          </div>
        </div>

        <div class="preview-footer">
          <button class="dark-btn" @click="closeMapPointGroup">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="previewAsset" class="preview-mask" @click.self="closePreview">
      <div class="preview-modal">
        <div class="preview-header">
          <div>
            <h2>{{ assetFilename(previewAsset) }}</h2>
            <p>#{{ previewAsset.id }} · 项目 ID：{{ previewAsset.project_id }}</p>
          </div>

          <button class="close-btn" @click="closePreview">×</button>
        </div>

        <div class="preview-body">
          <img v-if="assetPreviewUrl(previewAsset)" :src="assetPreviewUrl(previewAsset)" :alt="assetFilename(previewAsset)" />
          <div v-else class="empty-box">暂无预览图</div>
        </div>

        <div class="preview-info">
          <p><strong>拍摄时间：</strong>{{ formatDate(previewAsset.shot_at) }}</p>
          <p><strong>是否有 GPS：</strong>{{ gpsText(previewAsset) }}</p>
          <p><strong>GPS 来源：</strong>{{ gpsSourceText(previewAsset) }}</p>
          <p><strong>GPS 状态：</strong>{{ gpsStatusText(previewAsset) }}</p>
          <p><strong>GPS 坐标：</strong>{{ assetCoordinateText(previewAsset) }}</p>
          <p><strong>处理状态：</strong>{{ assetStatusText(previewAsset) }}</p>
        </div>

        <div class="preview-footer">
          <button class="light-btn" @click="openMedia(assetOriginalUrl(previewAsset))">打开原图</button>
          <button class="light-btn" @click="openMedia(assetPreviewUrl(previewAsset))">打开预览图</button>
          <button class="dark-btn" @click="closePreview">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>
