import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Camera,
  CheckCircle2,
  ArrowRight,
  ChevronDown,
  Plus,
} from 'lucide-react';
import FarmMap from './FarmMap';

interface TreeGroup {
  species: string;
  count: number;
  planting_date: string;
  category: 'Newly planted' | 'Existing trees';
}

export default function RegisterFarm() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<number>(1);

  // Form State
  const [farmName, setFarmName] = useState('Green Valley Farm');
  const [state, setState] = useState('Ogun');
  const [lga, setLga] = useState('Abeokuta North');
  const [community, setCommunity] = useState('Abeokuta');
  const [farmingType, setFarmingType] = useState('Agroforestry');

  // Boundary State
  const [boundaryMethod, setBoundaryMethod] = useState<'tap' | 'gps'>('gps');
  const [areaHa, setAreaHa] = useState<number>(2.5);
  const [polygonCoords, setPolygonCoords] = useState<[number, number][]>([]);

  // Tree State
  const [treeGroups, setTreeGroups] = useState<TreeGroup[]>([
    {
      species: 'Mango',
      count: 250,
      planting_date: 'Approx. 2025',
      category: 'Newly planted',
    },
  ]);

  // Evidence Photos State
  const [photosUploaded, setPhotosUploaded] = useState({
    wide: true,
    tree: true,
    closeUp: true,
  });

  // Confirmation
  const [confirmed, setConfirmed] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Submit Plot
  const handleSubmitFarm = async () => {
    setSubmitting(true);
    // Convert to GeoJSON [lng, lat]
    const coords =
      polygonCoords.length >= 3
        ? [polygonCoords.map(([lat, lng]) => [lng, lat])]
        : [[[3.344, 7.155], [3.348, 7.155], [3.348, 7.158], [3.344, 7.158], [3.344, 7.155]]];

    try {
      await fetch('/api/plots', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-EcoTrees': '1' },
        body: JSON.stringify({
          geometry: {
            type: 'Polygon',
            coordinates: coords,
          },
          plantings: [
            {
              species_code: 'MANGO',
              tree_count: treeGroups[0].count,
              planted_on: '2025-06-01',
            },
          ],
        }),
      }).catch(() => null);
    } finally {
      setSubmitting(false);
      setCurrentStep(6);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* STEP 1: Farm Information */}
      {currentStep === 1 && (
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Farm information
            </h1>
            <p className="text-sm text-gray-600 mt-1.5">
              First, tell us a little about the farm.
            </p>
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mt-3">
              Step 1 of 3 · Farm details
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
            <div className="md:col-span-8 bg-white rounded-2xl border border-gray-100 p-8 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-5">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  Farm name *
                </label>
                <input
                  type="text"
                  value={farmName}
                  onChange={(e) => setFarmName(e.target.value)}
                  placeholder="e.g. Green Valley Farm"
                  className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    State
                  </label>
                  <div className="relative">
                    <select
                      value={state}
                      onChange={(e) => {
                        const nextState = e.target.value;
                        setState(nextState);
                        if (nextState === 'Ogun') {
                          setLga('Abeokuta North');
                          setCommunity('Abeokuta');
                        } else if (nextState === 'Oyo') {
                          setLga('Ibadan');
                          setCommunity('Ibadan');
                        } else if (nextState === 'Osun') {
                          setLga('Osogbo');
                          setCommunity('Osogbo');
                        } else if (nextState === 'Lagos') {
                          setLga('Ikeja');
                          setCommunity('Ikeja');
                        }
                      }}
                      className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none appearance-none bg-white pr-9"
                    >
                      <option value="Ogun">Ogun State</option>
                      <option value="Oyo">Oyo State</option>
                      <option value="Osun">Osun State</option>
                      <option value="Lagos">Lagos State</option>
                    </select>
                    <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Local government area
                  </label>
                  <div className="relative">
                    <select
                      value={lga}
                      onChange={(e) => {
                        setLga(e.target.value);
                        setCommunity(e.target.value);
                      }}
                      className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none appearance-none bg-white pr-9"
                    >
                      {state === 'Ogun' && (
                        <>
                          <option value="Abeokuta North">Abeokuta North</option>
                          <option value="Abeokuta South">Abeokuta South</option>
                          <option value="Ijebu Ode">Ijebu Ode</option>
                          <option value="Ota">Ota / Ado-Odo</option>
                          <option value="Sagamu">Sagamu</option>
                        </>
                      )}
                      {state === 'Oyo' && (
                        <>
                          <option value="Ibadan">Ibadan Central</option>
                          <option value="Ogbomoso">Ogbomoso</option>
                          <option value="Oyo">Oyo East</option>
                        </>
                      )}
                      {state === 'Osun' && (
                        <>
                          <option value="Osogbo">Osogbo</option>
                          <option value="Ile-Ife">Ile-Ife</option>
                        </>
                      )}
                      {state === 'Lagos' && (
                        <>
                          <option value="Ikeja">Ikeja</option>
                          <option value="Epe">Epe</option>
                          <option value="Badagry">Badagry</option>
                        </>
                      )}
                    </select>
                    <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Community / village
                  </label>
                  <input
                    type="text"
                    value={community}
                    onChange={(e) => setCommunity(e.target.value)}
                    placeholder="Enter community"
                    className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Farming type
                  </label>
                  <div className="relative">
                    <select
                      value={farmingType}
                      onChange={(e) => setFarmingType(e.target.value)}
                      className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none appearance-none bg-white pr-9"
                    >
                      <option value="Agroforestry">Agroforestry / Orchard / Other</option>
                      <option value="Woodlot">Woodlot</option>
                      <option value="Regenerative">Regenerative Agroecology</option>
                    </select>
                    <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => setCurrentStep(2)}
                  className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-6 py-3.5 rounded-xl transition-colors cursor-pointer"
                >
                  Continue to farm location
                </button>
              </div>
            </div>

            <div className="md:col-span-4 bg-[#f2f7f4] rounded-2xl p-6">
              <h3 className="font-bold text-sm text-gray-900">
                One account, many farms
              </h3>
              <p className="text-xs text-gray-600 mt-2 leading-relaxed">
                Give each farm a name so you can track them separately.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2: Farm Location / Boundary */}
      {currentStep === 2 && (
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Where is your farm?
            </h1>
            <p className="text-sm text-gray-600 mt-1.5">
              Find the farm on the map, then trace its edges.
            </p>
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mt-3">
              Step 2 of 3 · Farm location
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
            <div className="md:col-span-8 space-y-4">
              <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
                <label className="text-[11px] font-medium text-gray-400 block mb-1">
                  Search community or village
                </label>
                <input
                  type="text"
                  value={community}
                  onChange={(e) => setCommunity(e.target.value)}
                  placeholder="Search location (e.g. Abeokuta, Ijebu, Ibadan)"
                  className="text-xs text-gray-900 outline-none w-full"
                />
              </div>

              {/* Real Interactive Leaflet Map */}
              <FarmMap
                stateName={state}
                lgaName={lga}
                communityName={community}
                boundaryMethod={boundaryMethod}
                onAreaChange={setAreaHa}
                onPolygonChange={setPolygonCoords}
              />
            </div>

            {/* Right Boundary Options */}
            <div className="md:col-span-4 space-y-4">
              <h3 className="font-semibold text-sm text-gray-900">
                Choose how to mark your boundary
              </h3>

              <div className="space-y-2.5">
                <button
                  onClick={() => setBoundaryMethod('tap')}
                  className={`w-full py-3.5 px-4 rounded-xl text-xs font-semibold border transition-all text-left ${
                    boundaryMethod === 'tap'
                      ? 'border-[#1b4332] bg-white text-[#1b4332] shadow-xs'
                      : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  Tap map corners
                </button>

                <button
                  onClick={() => setBoundaryMethod('gps')}
                  className={`w-full py-3.5 px-4 rounded-xl text-xs font-semibold border transition-all text-left ${
                    boundaryMethod === 'gps'
                      ? 'border-[#1b4332] bg-white text-[#1b4332] shadow-xs'
                      : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  Walk around farm (GPS)
                </button>
              </div>

              <div className="bg-[#f2f7f4] rounded-2xl p-5">
                <h4 className="font-semibold text-xs text-gray-900">Need help?</h4>
                <p className="text-[11px] text-gray-600 mt-1 leading-relaxed">
                  A field agent or cooperative representative can help map your farm.
                </p>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => setCurrentStep(3)}
                  className="w-full bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold py-3.5 rounded-xl transition-colors cursor-pointer"
                >
                  Save boundary &amp; continue
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STEP 3: Tree Details */}
      {currentStep === 3 && (
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Tell us about your trees
            </h1>
            <p className="text-sm text-gray-600 mt-1.5">
              Wetin you get for this farm?
            </p>
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mt-3">
              Step 3 of 3 · Tree details
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
            <div className="md:col-span-8 bg-white rounded-2xl border border-gray-100 p-8 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-6">
              <h3 className="font-bold text-sm text-gray-900">Tree group 01</h3>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                  Tree species *
                </label>
                <div className="relative">
                  <select
                    value={treeGroups[0].species}
                    onChange={(e) => {
                      const updated = [...treeGroups];
                      updated[0].species = e.target.value;
                      setTreeGroups(updated);
                    }}
                    className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none appearance-none bg-white pr-9"
                  >
                    <option value="Mango">Mango</option>
                    <option value="Gmelina">Gmelina</option>
                    <option value="Cashew">Cashew</option>
                    <option value="Teak">Teak</option>
                    <option value="Oil Palm">Oil Palm</option>
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Number of trees *
                  </label>
                  <input
                    type="number"
                    value={treeGroups[0].count}
                    onChange={(e) => {
                      const updated = [...treeGroups];
                      updated[0].count = Number(e.target.value);
                      setTreeGroups(updated);
                    }}
                    placeholder="e.g. 250 — estimate is okay"
                    className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">
                    Planting date
                  </label>
                  <input
                    type="text"
                    value={treeGroups[0].planting_date}
                    onChange={(e) => {
                      const updated = [...treeGroups];
                      updated[0].planting_date = e.target.value;
                      setTreeGroups(updated);
                    }}
                    placeholder="Choose date or approximate month"
                    className="w-full text-xs text-gray-900 px-4 py-3 rounded-xl border border-gray-200 focus:border-[#1b4332] outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-2">
                  Tree category
                </label>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      const updated = [...treeGroups];
                      updated[0].category = 'Newly planted';
                      setTreeGroups(updated);
                    }}
                    className={`px-5 py-2.5 rounded-xl text-xs font-semibold border transition-all ${
                      treeGroups[0].category === 'Newly planted'
                        ? 'bg-white border-[#1b4332] text-[#1b4332] shadow-xs'
                        : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Newly planted
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      const updated = [...treeGroups];
                      updated[0].category = 'Existing trees';
                      setTreeGroups(updated);
                    }}
                    className={`px-5 py-2.5 rounded-xl text-xs font-semibold border transition-all ${
                      treeGroups[0].category === 'Existing trees'
                        ? 'bg-white border-[#1b4332] text-[#1b4332] shadow-xs'
                        : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Existing trees
                  </button>
                </div>
              </div>

              <button
                type="button"
                className="flex items-center gap-2 border border-gray-200 hover:bg-gray-50 text-gray-800 text-xs font-semibold px-4 py-2.5 rounded-xl transition-colors cursor-pointer"
              >
                <span>Add another tree group</span>
                <Plus size={14} />
              </button>

              <div className="pt-2">
                <button
                  onClick={() => setCurrentStep(4)}
                  className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-6 py-3.5 rounded-xl transition-colors cursor-pointer"
                >
                  Continue to evidence
                </button>
              </div>
            </div>

            <div className="md:col-span-4 bg-[#f2f7f4] rounded-2xl p-6">
              <h3 className="font-bold text-sm text-gray-900">
                Mixed farms are welcome
              </h3>
              <p className="text-xs text-gray-600 mt-2 leading-relaxed">
                Add a separate group for each species and its estimated count.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* STEP 4: Evidence Photos */}
      {currentStep === 4 && (
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Show us your farm
            </h1>
            <p className="text-sm text-gray-600 mt-1.5">
              A few clear photos will help our team understand your farm.
            </p>
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mt-3">
              Evidence checklist · 3 of 3
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Card 1: Wide farm photo */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between h-64">
              <div>
                <Camera size={22} className="text-[#1b4332] mb-3" />
                <h3 className="font-bold text-sm text-gray-900">
                  Required · Wide farm photo
                </h3>
                <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                  Capture a wide view of the farm so reviewers can understand the site.
                </p>
              </div>
              <button
                onClick={() => setPhotosUploaded({ ...photosUploaded, wide: !photosUploaded.wide })}
                className="w-full border border-gray-200 hover:bg-gray-50 text-gray-800 text-xs font-semibold py-2.5 rounded-xl transition-colors"
              >
                {photosUploaded.wide ? 'Retake farm photo' : 'Take farm photo'}
              </button>
            </div>

            {/* Card 2: Tree photos */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between h-64">
              <div>
                <Camera size={22} className="text-[#1b4332] mb-3" />
                <h3 className="font-bold text-sm text-gray-900">
                  Required · Tree photos
                </h3>
                <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                  Show the trees clearly. Add more than one photo if needed.
                </p>
              </div>
              <button
                onClick={() => setPhotosUploaded({ ...photosUploaded, tree: !photosUploaded.tree })}
                className="w-full border border-gray-200 hover:bg-gray-50 text-gray-800 text-xs font-semibold py-2.5 rounded-xl transition-colors"
              >
                {photosUploaded.tree ? 'Retake tree photos' : 'Add tree photos'}
              </button>
            </div>

            {/* Card 3: Close-up photo */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between h-64">
              <div>
                <Camera size={22} className="text-[#1b4332] mb-3" />
                <h3 className="font-bold text-sm text-gray-900">
                  Recommended · Close-up photo
                </h3>
                <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                  Show leaves, trunks or young trees.
                </p>
              </div>
              <button
                onClick={() => setPhotosUploaded({ ...photosUploaded, closeUp: !photosUploaded.closeUp })}
                className="w-full border border-gray-200 hover:bg-gray-50 text-gray-800 text-xs font-semibold py-2.5 rounded-xl transition-colors"
              >
                {photosUploaded.closeUp ? 'Retake close-up' : 'Add close-up photo'}
              </button>
            </div>
          </div>

          <p className="text-xs text-gray-400">
            Uploaded photos appear here as thumbnails. Retake or remove before submitting.
          </p>

          <div className="bg-[#f2f7f4] rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="font-bold text-sm text-gray-900">Low network?</h4>
              <p className="text-xs text-gray-600 mt-1">
                No wahala if your network drops. Your draft stays saved, and you can try the photos again later.
              </p>
            </div>

            <button
              onClick={() => setCurrentStep(5)}
              className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-6 py-3.5 rounded-xl transition-colors cursor-pointer shrink-0"
            >
              Review my submission
            </button>
          </div>
        </div>
      )}

      {/* STEP 5: Review Submission */}
      {currentStep === 5 && (
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Review your farm
            </h1>
            <p className="text-sm text-gray-600 mt-1.5">
              Take one last look. You can still change anything here.
            </p>
          </div>

          {/* 4 Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Card 1: Farm info */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
              <div>
                <h3 className="font-bold text-sm text-gray-900">Farm information</h3>
                <p className="text-xs text-gray-600 mt-3">
                  {farmName} · {community}, {state} · {farmingType}
                </p>
              </div>
              <button
                onClick={() => setCurrentStep(1)}
                className="text-xs font-medium text-gray-700 hover:text-[#1b4332] flex items-center gap-1.5 mt-4 transition-colors text-left"
              >
                <span>Edit details</span>
                <ArrowRight size={13} />
              </button>
            </div>

            {/* Card 2: Boundary */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
              <div>
                <h3 className="font-bold text-sm text-gray-900">Farm boundary</h3>
                <p className="text-xs text-gray-600 mt-3">
                  Map preview · {areaHa} hectares · {boundaryMethod === 'gps' ? 'GPS walk-around' : 'Map corners'}
                </p>
              </div>
              <button
                onClick={() => setCurrentStep(2)}
                className="text-xs font-medium text-gray-700 hover:text-[#1b4332] flex items-center gap-1.5 mt-4 transition-colors text-left"
              >
                <span>Edit details</span>
                <ArrowRight size={13} />
              </button>
            </div>

            {/* Card 3: Tree info */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
              <div>
                <h3 className="font-bold text-sm text-gray-900">Tree information</h3>
                <p className="text-xs text-gray-600 mt-3">
                  {treeGroups[0].species} · {treeGroups[0].count} trees · {treeGroups[0].category}
                </p>
              </div>
              <button
                onClick={() => setCurrentStep(3)}
                className="text-xs font-medium text-gray-700 hover:text-[#1b4332] flex items-center gap-1.5 mt-4 transition-colors text-left"
              >
                <span>Edit details</span>
                <ArrowRight size={13} />
              </button>
            </div>

            {/* Card 4: Evidence */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
              <div>
                <h3 className="font-bold text-sm text-gray-900">Farm evidence</h3>
                <p className="text-xs text-gray-600 mt-3">
                  Farm photo · Tree photo · Close-up · 3 photos
                </p>
              </div>
              <button
                onClick={() => setCurrentStep(4)}
                className="text-xs font-medium text-gray-700 hover:text-[#1b4332] flex items-center gap-1.5 mt-4 transition-colors text-left"
              >
                <span>Edit details</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </div>

          {/* Confirmation Box */}
          <div
            onClick={() => setConfirmed(!confirmed)}
            className="bg-[#f2f7f4] rounded-2xl p-5 flex items-center gap-3 cursor-pointer"
          >
            <CheckCircle2 size={18} className={confirmed ? 'text-[#1b4332]' : 'text-gray-300'} />
            <span className="text-xs text-gray-800 font-medium">
              I confirm that this information is accurate to the best of my knowledge.
            </span>
          </div>

          <div>
            <button
              onClick={handleSubmitFarm}
              disabled={submitting || !confirmed}
              className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-6 py-3.5 rounded-xl transition-colors cursor-pointer disabled:opacity-60"
            >
              {submitting ? 'Submitting farm...' : 'Submit farm for review'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 6: Submission Successful */}
      {currentStep === 6 && (
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Submission successful!
            </h1>
            <p className="text-sm text-gray-600 mt-1.5">
              We’ve received your farm details. Our team will take a look.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
            {/* Left Big Card (8 cols) */}
            <div className="md:col-span-8 space-y-6">
              <div className="bg-[#f2f7f4] rounded-2xl p-8 flex items-start gap-4">
                <CheckCircle2 size={24} className="text-[#1b4332] shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-bold text-base text-gray-900">
                    Submission received
                  </h3>
                  <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                    Our team will check the details and photos you sent.
                  </p>
                </div>
              </div>

              {/* What happens next */}
              <div>
                <h3 className="font-bold text-sm text-gray-900 mb-4">
                  What happens next?
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-[#f2f7f4] rounded-2xl p-6 space-y-2">
                    <h4 className="font-bold text-xs text-gray-900">
                      1 · Team review
                    </h4>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      A reviewer will check your farm details, map and photos.
                    </p>
                  </div>

                  <div className="bg-[#f2f7f4] rounded-2xl p-6 space-y-2">
                    <h4 className="font-bold text-xs text-gray-900">
                      2 · Review decision
                    </h4>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      We notify you in-app if changes are needed or the project is internally approved.
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => navigate('/farmer/overview')}
                  className="bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold px-6 py-3.5 rounded-xl transition-colors cursor-pointer"
                >
                  Go to my dashboard
                </button>
              </div>
            </div>

            {/* Right Reference Box (4 cols) */}
            <div className="md:col-span-4 space-y-4">
              <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-3">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                  Project reference
                </span>
                <div className="text-lg font-bold text-gray-900">
                  ET-2026-00124
                </div>
                <div>
                  <span className="bg-[#fef3c7] text-[#92400e] text-xs font-semibold px-3 py-1 rounded-full">
                    Under review
                  </span>
                </div>
              </div>

              <div className="bg-[#fbf4e2] border border-[#f5e6c4] rounded-2xl p-6">
                <h4 className="font-bold text-sm text-[#543d11]">Important</h4>
                <p className="text-xs text-[#71541b] mt-1.5 leading-relaxed">
                  Under review does not mean approved or certified.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
