'use strict';

// IDs without a prefix refer to the original workcell and its Antigravity edition.
// An edition-specific entry takes precedence when a rebuild moved to a different room.
const sceneCollections = {
  'Bathroom': ['everyday_drawer', 'mobile_washroom'],
  'Café': ['legacy_03_cafe'],
  'Coffee roastery': ['mobile_roastery'],
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
