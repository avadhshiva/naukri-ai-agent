import fs from "node:fs";
import path from "node:path";

export type JobRecord = {
  title: string;
  company: string;
  location: string;
  salary: string;
  searchTitle: string;
  searchExperience: number;
  searchLocation: string;
  jobUrl: string;
  applyType: string;
  applied: boolean;
  status: string;
  notes: string;
  resumeUpdated?: boolean;
  postedDate?: string;
  lastCheckedAt?: string;
};

type JobsPayload = {
  generatedAt: string;
  jobCount: number;
  jobs: JobRecord[];
};

const jobsPath = path.resolve(process.cwd(), "..", "data", "jobs.json");

export function readJobsPayload(): JobsPayload {
  try {
    const raw = fs.readFileSync(jobsPath, "utf-8");
    return JSON.parse(raw) as JobsPayload;
  } catch {
    return {
      generatedAt: "",
      jobCount: 0,
      jobs: [],
    };
  }
}
