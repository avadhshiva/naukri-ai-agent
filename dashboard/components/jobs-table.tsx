import { JobRecord } from "../lib/data";

function formatApplyType(applyType: string) {
  if (applyType === "apply_on_company_site") return "Apply on company site";
  if (applyType === "apply") return "Apply";
  return "Review";
}

export function JobsTable({ jobs }: { jobs: JobRecord[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Role</th>
            <th>Company</th>
            <th>Location</th>
            <th>Salary</th>
            <th>Apply Type</th>
            <th>Applied</th>
            <th>Link</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job, index) => (
            <tr key={`${job.jobUrl}-${index}`}>
              <td>
                <strong>{job.title}</strong>
                <div className="subtle">
                  {job.searchTitle} | {job.searchExperience} yrs | {job.searchLocation}
                </div>
              </td>
              <td>{job.company}</td>
              <td>{job.location}</td>
              <td>{job.salary}</td>
              <td>{formatApplyType(job.applyType)}</td>
              <td>{job.applied ? "Yes" : "No"}</td>
              <td>
                <a className="job-link" href={job.jobUrl} target="_blank" rel="noreferrer">
                  Open job
                </a>
              </td>
              <td>{job.notes || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
