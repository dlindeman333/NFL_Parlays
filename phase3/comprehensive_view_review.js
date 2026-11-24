// Explicit review-only entry point; no network or storage access.
function mountComprehensiveReview(container, bundle, existingSheets) {
 if (!bundle || bundle.schema_version !== 4 ||
     !Array.isArray(bundle.dashboard?.individual) ||
     !Array.isArray(bundle.dashboard?.suggested_parlays) ||
     !bundle.workbook_tables || !Array.isArray(existingSheets)) {
   throw new Error('Invalid comprehensive review bundle');
 }
 // Validate workbook before modifying the dashboard.
 const sheets = comprehensiveWorkbookSheets(existingSheets, bundle.workbook_tables);
 renderComprehensivePerformance(container, bundle.dashboard);
 return sheets;
}
