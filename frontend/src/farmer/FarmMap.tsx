import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import { Crosshair, RotateCcw, Trash2 } from 'lucide-react';

interface FarmMapProps {
  stateName: string;
  lgaName: string;
  communityName: string;
  boundaryMethod: 'tap' | 'gps';
  onAreaChange?: (areaHa: number) => void;
  onPolygonChange?: (coords: [number, number][]) => void;
}

// Built-in Nigeria Geographic Index (State -> LGA/City -> [lat, lng, zoom])
const NIGERIA_LOCATIONS: Record<string, { lat: number; lng: number; zoom: number; lgas?: Record<string, [number, number]> }> = {
  Ogun: {
    lat: 7.0,
    lng: 3.4,
    zoom: 10,
    lgas: {
      Abeokuta: [7.1557, 3.3458],
      'Abeokuta North': [7.1850, 3.3150],
      'Abeokuta South': [7.1400, 3.3550],
      Ijebu: [6.8207, 3.9213],
      'Ijebu Ode': [6.8207, 3.9213],
      Ota: [6.6908, 3.2355],
      Sagamu: [6.8482, 3.6465],
    },
  },
  Oyo: {
    lat: 7.8,
    lng: 3.9,
    zoom: 9,
    lgas: {
      Ibadan: [7.3775, 3.9470],
      'Ibadan Central': [7.3775, 3.9470],
      Ogbomoso: [8.1333, 4.2400],
      Oyo: [7.8500, 3.9333],
      'Oyo East': [7.8500, 3.9333],
    },
  },
  Osun: {
    lat: 7.6,
    lng: 4.5,
    zoom: 10,
    lgas: {
      Osogbo: [7.7827, 4.5418],
      'Ile-Ife': [7.4912, 4.5615],
    },
  },
  Lagos: {
    lat: 6.55,
    lng: 3.38,
    zoom: 11,
    lgas: {
      Ikeja: [6.6018, 3.3515],
      Epe: [6.5841, 3.9834],
      Badagry: [6.4316, 2.8876],
    },
  },
};

// Calculate geodesic polygon area in hectares
function calculatePolygonAreaHa(coords: [number, number][]): number {
  if (coords.length < 3) return 0;
  const radius = 6378137; // Earth radius in meters
  let area = 0;
  const len = coords.length;

  for (let i = 0; i < len; i++) {
    const p1 = coords[i];
    const p2 = coords[(i + 1) % len];
    const lat1 = (p1[0] * Math.PI) / 180;
    const lat2 = (p2[0] * Math.PI) / 180;
    const lon1 = (p1[1] * Math.PI) / 180;
    const lon2 = (p2[1] * Math.PI) / 180;
    area += (lon2 - lon1) * (2 + Math.sin(lat1) + Math.sin(lat2));
  }

  area = Math.abs((area * radius * radius) / 2);
  const ha = area / 10000;
  return Number(ha.toFixed(2));
}

export default function FarmMap({
  stateName,
  lgaName,
  communityName,
  boundaryMethod,
  onAreaChange,
  onPolygonChange,
}: FarmMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const polygonLayerRef = useRef<L.Polygon | null>(null);
  const markersGroupRef = useRef<L.LayerGroup | null>(null);

  const [mapType, setMapType] = useState<'standard' | 'satellite'>('standard');
  const [polygonPoints, setPolygonPoints] = useState<[number, number][]>([
    [7.1575, 3.3440],
    [7.1585, 3.3475],
    [7.1550, 3.3485],
    [7.1535, 3.3455],
    [7.1555, 3.3435],
  ]);

  const currentArea = calculatePolygonAreaHa(polygonPoints);

  const updatePolygonPoints = useCallback(
    (newPoints: [number, number][]) => {
      setPolygonPoints(newPoints);
      const ha = calculatePolygonAreaHa(newPoints);
      onAreaChange?.(ha);
      onPolygonChange?.(newPoints);
    },
    [onAreaChange, onPolygonChange]
  );

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Default center in Ogun State / Abeokuta
    const map = L.map(mapContainerRef.current, {
      center: [7.1557, 3.3458],
      zoom: 13,
      zoomControl: false,
    });

    // Add standard OSM tile layer
    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    tileLayerRef.current = osmLayer;
    markersGroupRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    // Handle clicks for "Tap map corners" mode
    map.on('click', (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;
      setPolygonPoints((prev) => {
        const next: [number, number][] = [...prev, [lat, lng]];
        onAreaChange?.(calculatePolygonAreaHa(next));
        onPolygonChange?.(next);
        return next;
      });
    });

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [onAreaChange, onPolygonChange]);

  // Update Tile Layer when user toggles Standard vs Satellite
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current);
    }

    if (mapType === 'satellite') {
      tileLayerRef.current = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
          maxZoom: 18,
          attribution: 'Tiles &copy; Esri &mdash; Source: Esri, USDA, USGS',
        }
      ).addTo(map);
    } else {
      tileLayerRef.current = L.tileLayer(
        'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        {
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap contributors',
        }
      ).addTo(map);
    }
  }, [mapType]);

  // Zoom / Focus Map when State, LGA, or Community changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    let targetLat = 7.1557;
    let targetLng = 3.3458;
    let targetZoom = 13;

    const stateData = NIGERIA_LOCATIONS[stateName];
    if (stateData) {
      targetLat = stateData.lat;
      targetLng = stateData.lng;
      targetZoom = stateData.zoom;

      // Check for matching LGA
      if (stateData.lgas) {
        for (const [lgaKey, coords] of Object.entries(stateData.lgas)) {
          if (
            lgaName.toLowerCase().includes(lgaKey.toLowerCase()) ||
            lgaKey.toLowerCase().includes(lgaName.toLowerCase())
          ) {
            targetLat = coords[0];
            targetLng = coords[1];
            targetZoom = 14;
            break;
          }
        }
      }
    }

    // Smoothly fly to the location
    map.flyTo([targetLat, targetLng], targetZoom, {
      duration: 1.2,
    });
  }, [stateName, lgaName, communityName]);

  // Synchronize Leaflet Layers whenever polygonPoints changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear previous polygon and markers
    if (polygonLayerRef.current) {
      map.removeLayer(polygonLayerRef.current);
      polygonLayerRef.current = null;
    }

    if (markersGroupRef.current) {
      markersGroupRef.current.clearLayers();
    }

    if (polygonPoints.length === 0) return;

    // Add circle marker at each corner point
    polygonPoints.forEach((pt, index) => {
      const circleMarker = L.circleMarker(pt, {
        radius: 5,
        color: '#1b4332',
        fillColor: '#ffffff',
        fillOpacity: 1,
        weight: 2,
      });
      circleMarker.bindTooltip(`Point ${index + 1}`, { permanent: false });
      markersGroupRef.current?.addLayer(circleMarker);
    });

    if (polygonPoints.length >= 3) {
      // Draw green dashed polygon matching design
      const poly = L.polygon(polygonPoints, {
        color: '#1b4332',
        weight: 2.5,
        dashArray: '6, 8',
        fillColor: '#1b4332',
        fillOpacity: 0.15,
      }).addTo(map);

      polygonLayerRef.current = poly;
    }
  }, [polygonPoints]);

  // Handle GPS Walk-Around Simulation
  useEffect(() => {
    if (boundaryMethod === 'gps') {
      const map = mapInstanceRef.current;
      if (!map) return;

      const center = map.getCenter();
      const deltaLat = 0.0025;
      const deltaLng = 0.003;

      // 5 perimeter points around center
      const gpsPerimeter: [number, number][] = [
        [center.lat + deltaLat * 0.8, center.lng - deltaLng * 0.7],
        [center.lat + deltaLat, center.lng + deltaLng * 0.6],
        [center.lat - deltaLat * 0.2, center.lng + deltaLng * 0.9],
        [center.lat - deltaLat, center.lng],
        [center.lat - deltaLat * 0.6, center.lng - deltaLng * 0.8],
      ];

      updatePolygonPoints(gpsPerimeter);
    }
  }, [boundaryMethod, updatePolygonPoints]);

  // Recenter map on current location
  const handleCurrentLocation = useCallback(() => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        const map = mapInstanceRef.current;
        if (map) {
          map.flyTo([latitude, longitude], 15);
          L.circleMarker([latitude, longitude], {
            radius: 7,
            color: '#1b4332',
            fillColor: '#1b4332',
            fillOpacity: 0.9,
          })
            .bindTooltip('Your current GPS location', { permanent: true })
            .addTo(map);
        }
      },
      () => {
        alert('Could not retrieve GPS location. Ensure location permissions are enabled.');
      }
    );
  }, []);

  const handleUndoPoint = () => {
    updatePolygonPoints(polygonPoints.slice(0, -1));
  };

  const handleClearPolygon = () => {
    updatePolygonPoints([]);
  };

  return (
    <div className="space-y-3">
      {/* Interactive Map Canvas Box */}
      <div className="relative rounded-2xl overflow-hidden border border-gray-200/90 shadow-xs h-80 bg-[#eaf3ec]">
        <div ref={mapContainerRef} className="w-full h-full z-0" />

        {/* Floating Declared Area Badge */}
        <div className="absolute top-4 left-4 z-10 bg-white/95 backdrop-blur-xs border border-gray-200/80 px-3.5 py-1.5 rounded-full shadow-xs flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#1b4332] animate-pulse" />
          <span className="text-xs font-semibold text-gray-900">
            Declared area: {currentArea} ha
          </span>
          <span className="text-[10px] text-gray-400">
            ({polygonPoints.length} points)
          </span>
        </div>

        {/* Map Type Toggle: Standard vs Satellite */}
        <div className="absolute bottom-4 left-4 z-10 bg-white/95 backdrop-blur-xs border border-gray-200 px-3 py-1 rounded-xl text-xs flex items-center gap-2 shadow-xs">
          <button
            type="button"
            onClick={() => setMapType('standard')}
            className={`font-medium transition-colors cursor-pointer ${
              mapType === 'standard' ? 'text-[#1b4332] font-bold' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            Standard map
          </button>
          <span className="text-gray-300">|</span>
          <button
            type="button"
            onClick={() => setMapType('satellite')}
            className={`font-medium transition-colors cursor-pointer ${
              mapType === 'satellite' ? 'text-[#1b4332] font-bold' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            Satellite view
          </button>
        </div>

        {/* Map Tools on the Right */}
        <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
          <button
            type="button"
            onClick={handleCurrentLocation}
            title="Focus current GPS location"
            className="bg-white/95 hover:bg-white p-2.5 rounded-xl border border-gray-200 shadow-xs text-gray-700 hover:text-[#1b4332] transition-colors cursor-pointer"
          >
            <Crosshair size={16} />
          </button>

          {polygonPoints.length > 0 && (
            <>
              <button
                type="button"
                onClick={handleUndoPoint}
                title="Undo last point"
                className="bg-white/95 hover:bg-white p-2.5 rounded-xl border border-gray-200 shadow-xs text-gray-700 hover:text-amber-700 transition-colors cursor-pointer"
              >
                <RotateCcw size={16} />
              </button>
              <button
                type="button"
                onClick={handleClearPolygon}
                title="Clear boundary"
                className="bg-white/95 hover:bg-white p-2.5 rounded-xl border border-gray-200 shadow-xs text-gray-700 hover:text-red-600 transition-colors cursor-pointer"
              >
                <Trash2 size={16} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Helper beneath map */}
      <div className="flex items-center justify-between text-xs text-gray-500 pt-1">
        <button
          type="button"
          onClick={handleCurrentLocation}
          className="bg-white border border-gray-200 hover:bg-gray-50 text-gray-800 text-xs font-semibold px-4 py-2.5 rounded-xl transition-colors cursor-pointer"
        >
          Use my current location
        </button>

        <span className="text-[11px] text-gray-400">
          {boundaryMethod === 'tap'
            ? 'Click on the map to place boundary corner markers.'
            : 'Simulating walk-around boundary trace.'}
        </span>
      </div>
    </div>
  );
}
