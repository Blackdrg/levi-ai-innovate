// frontend_react/src/lib/indexeddb.ts
import { openDB, IDBPDatabase } from 'idb';

/**
 * Sovereign v15.0: Cognitive Cache (IndexedDB).
 * Persists mission history and telemetry locally for offline/resilient analysis.
 */

const DB_NAME = 'levi-cognitive-cache';
const VERSION = 1;

export interface MissionData {
  id: string;
  data: any;
  timestamp: number;
}

export const initDB = async (): Promise<IDBPDatabase> => {
  return openDB(DB_NAME, VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('missions')) {
        db.createObjectStore('missions', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('telemetry')) {
        db.createObjectStore('telemetry', { keyPath: 'id', autoIncrement: true });
      }
    },
  });
};

export const saveMission = async (mission: MissionData) => {
  const db = await initDB();
  await db.put('missions', mission);
};

export const getMission = async (id: string) => {
  const db = await initDB();
  return db.get('missions', id);
};

export const getAllMissions = async () => {
  const db = await initDB();
  return db.getAll('missions');
};

export const clearCache = async () => {
  const db = await initDB();
  await db.clear('missions');
  await db.clear('telemetry');
};
