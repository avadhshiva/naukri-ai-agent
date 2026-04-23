import { JobsTable } from "../components/jobs-table";
import { Metrics } from "../components/metrics";
import { readJobsPayload } from "../lib/data";

export const dynamic = "force-dynamic";

export default function HomePage() {
  const payload = readJobsPayload();
  const jobs = payload.jobs;
  const applied = jobs.filter((job) => job.applied).length;
  const companySite = jobs.filter((job) => job.applyType === "apply_on_company_site").length;
  const directApply = jobs.filter((job) => job.applyType === "apply").length;
  const newest = jobs.slice(0, 5);

  return (
    <main className="page-shell">
      <section className="hero">
        <h1>Playwright Naukri Agent</h1>
        <p>
          Python drives the Naukri browser flow, Groq answers short screening prompts, and this
          React dashboard shows every captured opening with apply type, job link, and application status.
        </p>
      </section>

      <Metrics total={jobs.length} applied={applied} companySite={companySite} directApply={directApply} />

      <section className="grid-2">
        <article className="panel">
          <h2>All Job Openings</h2>
          <p className="subtle">
            Generated at: {payload.generatedAt || "No run yet"}. Run the Python agent to refresh `data/jobs.json`.
          </p>
          <JobsTable jobs={jobs} />
        </article>

        <article className="panel">
          <h2>Latest Activity</h2>
          <p className="subtle">Recent jobs with the action the agent observed.</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Apply Type</th>
                  <th>Applied</th>
                  <th>Checked</th>
                </tr>
              </thead>
              <tbody>
                {newest.length > 0 ? (
                  newest.map((job, index) => (
                    <tr key={`${job.jobUrl}-mini-${index}`}>
                      <td>
                        <strong>{job.title}</strong>
                        <div className="subtle">{job.company}</div>
                      </td>
                      <td>{job.applyType === "apply_on_company_site" ? "Apply on company site" : job.applyType === "apply" ? "Apply" : "Review"}</td>
                      <td>
                        {job.applied ? "Yes" : "No"}
                      </td>
                      <td>{job.lastCheckedAt || "-"}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4}>No jobs captured yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </main>
  );
}
