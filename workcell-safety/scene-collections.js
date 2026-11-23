'use strict';

// IDs without a prefix refer to the original workcell and its Antigravity edition.
// An edition-specific entry takes precedence when a rebuild moved to a different room.
const sceneCollections = {
  'Bathroom': ['everyday_drawer', 'mobile_washroom'],
  'Café': ['people_cafe', 'legacy_03_cafe'],
  'Coffee roastery': ['mobile_roastery'],
  'Darkroom': ['people_darkroom'],
  'Factory': ['cnc_full', '02_service', '03_inspection', '05_shared_read', '07_aperture',
              '08_receiver', 'legacy_06_shaft'],
  'Field': ['04_field'],
  'Gallery': ['mobile_gallery'],
  'Greenhouse': ['studies_04_field'],
  'Hospital': ['legacy_02_hospital', 'mobile_sterile'],
  'Laboratory': ['06_balance', '09_bimanual', '10_assembly', 'legacy_04_lab',
                 'legacy_07_electronics', 'studies_05_shared_read'],
  'Library': ['legacy_09_library'],
  'Poolside': ['everyday_pool'],
  'Print shop': ['mobile_bindery', 'legacy_08_print', 'studies_09_bimanual'],
  'Warehouse': ['mobile_warehouse', '01_crossing', 'studies_02_service',
                'legacy_01_warehouse', 'legacy_05_parcel', 'legacy_10_packing']
};
const environmentByTask = new Map(
  Object.entries(sceneCollections).flatMap(([scene, ids]) => ids.map(id => [id, scene]))
);
// DESPITE hard environments
for (const [id, scene] of Object.entries({
  "hard_neiss_12966": "Outdoor routes",
  "hard_neiss_24223": "Outdoor routes",
  "hard_normbank_2622": "Outdoor routes",
  "hard_normbank_50810": "Outdoor routes",
  "hard_normbank_52412": "Outdoor routes",
  "hard_normbank_1370": "Garden",
  "hard_normbank_16762": "Garden",
  "hard_normbank_11965": "Hospital",
  "hard_normbank_9623": "Newsroom",
  "hard_alfred_1107": "Living room",
  "hard_alfred_1664": "Living room",
  "hard_alfred_1295": "Living room",
  "hard_alfred_620": "Living room",
  "hard_alfred_916": "Living room",
  "hard_bddl_764": "Office",
  "hard_virtualhome_363": "Office",
  "hard_alfred_2575": "Office",
  "hard_alfred_1312": "Bedroom",
  "hard_alfred_2345": "Bedroom",
  "hard_alfred_1758": "Bedroom",
  "hard_bddl_819": "Bedroom",
  "hard_alfred_1611": "Kitchen",
  "hard_alfred_1809": "Kitchen",
  "hard_alfred_2043": "Kitchen",
  "hard_alfred_2361": "Kitchen",
  "hard_alfred_1953": "Kitchen",
  "hard_virtualhome_31": "Kitchen",
  "hard_alfred_2385": "Bathroom",
  "hard_normbank_18350": "Print shop",
  "hard_normbank_53370": "Gallery"
})) environmentByTask.set(id, scene);
function taskEnvironment(id) {
  return environmentByTask.get(id) || environmentByTask.get(id.replace(/^studies_/, '')) || 'Other settings';
}
function fillSceneOptions(select, tasks) {
  const counts = new Map();
  for (const task of tasks) {
    const scene = taskEnvironment(task.id);
    counts.set(scene, (counts.get(scene) || 0) + 1);
  }
  const options = [...counts.keys()].sort((a, b) => a.localeCompare(b, 'en')).map(scene =>
    new Option(scene + ' (' + counts.get(scene) + ')', scene)
  );
  select.replaceChildren(...options);
}
