// Add ONLY to a new standalone job-discovery project with no existing doPost.
// Do not replace a Gmail project's existing entry point.
function doPost(e) {
  return jobDiscoveryHandlePost(e);
}
