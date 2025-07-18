# TCGA-Histology-Hub
Central hub for TCGA histology data.


## Prerequisites

- **Python 3.6+**: Ensure Python is installed.
- **Required Libraries**: Install the necessary Python libraries using:
  ```bash
  pip install requests tenacity pandas
  ```
- **Internet Access**: Required to query the GDC API and download files.
- **Storage Space**: If downloading slides, ensure sufficient disk space (slides can be large, e.g., ~1TB for TCGA-BRCA).

## Script Overview

The script downloads metadata and optionally slide images (SVS format) for selected TCGA projects, organizes them by patient (using `case_id` or `cases.submitter_id`), and supports filtering by patient IDs. It generates:
- Per-project CSV summaries (`tcga_data/<project_id>_summary.csv`) with total patients, total slides, tissue slides, diagnostic slides, size (MB), file formats, and per-patient details.
- A single summary CSV (`tcga_data/all_tcga_projects_summary.csv`) aggregating data across all specified projects.
- A log file (`tcga_download_log.txt`) capturing all output and errors.

Supported TCGA projects:
- TCGA-BRCA, TCGA-LUAD, TCGA-LUSC, TCGA-OV, TCGA-GBM, TCGA-UCEC, TCGA-COAD, TCGA-PRAD, TCGA-THCA, TCGA-HNSC, TCGA-LIHC

## Usage Instructions

1. **Save the Script**:
   - Save the script as `gdc-wsi-downloader.py.py` in your working directory.

2. **Prepare Patient IDs (Optional)**:
   - **CSV File**: Create a CSV file (e.g., `patient_ids.csv`) with a `Patient ID` column containing patient IDs (e.g., `TCGA-XX-XXXX`). Example:
     ```csv
     Patient ID
     TCGA-A1-XXXX
     TCGA-A2-YYYY
     ```
   - **Comma-Separated String**: List patient IDs directly, e.g., `TCGA-XX-XXXX,TCGA-YY-YYYY`.
   - If no patient IDs are provided, the script processes all patients for the specified projects.

3. **Run the Script**:
   - Use the command line with the following arguments:
     - `--download-type`: Specifies what to download:
       - `tissue`: Download tissue slides and metadata.
       - `diagnostic`: Download diagnostic slides and metadata.
       - `both`: Download both tissue and diagnostic slides and metadata.
       - `none`: Download metadata only.
     - `--projects`: Specifies TCGA projects to process:
       - `all`: Process all 11 projects listed above.
       - A single project ID (e.g., `TCGA-BRCA`).
       - Comma-separated project IDs (e.g., `TCGA-BRCA,TCGA-LUAD,TCGA-OV`).
     - `--patient-ids`: Filters downloads to specific patients:
       - Path to a CSV file with a `Patient ID` column (e.g., `patient_ids.csv`).
       - Comma-separated patient IDs (e.g., `TCGA-XX-XXXX,TCGA-YY-YYYY`).
       - Omit to process all patients.

   **Examples**:
   - Download tissue slides and metadata for specific patients in TCGA-BRCA using a CSV file:
     ```bash
     python gdc-wsi-downloader.py.py --download-type tissue --projects TCGA-BRCA --patient-ids patient_ids.csv
     ```
   - Download both tissue and diagnostic slides for specific patients across TCGA-BRCA and TCGA-LUAD using a comma-separated string:
     ```bash
     python gdc-wsi-downloader.py.py --download-type both --projects TCGA-BRCA,TCGA-LUAD --patient-ids TCGA-A1-XXXX,TCGA-A2-YYYY
     ```
   - Download diagnostic slides and metadata for all patients in all projects:
     ```bash
     python gdc-wsi-downloader.py.py --download-type diagnostic --projects all
     ```
   - Download metadata only for a specific patient in TCGA-OV:
     ```bash
     python gdc-wsi-downloader.py.py --download-type none --projects TCGA-OV --patient-ids TCGA-ZZ-ZZZZ
     ```

4. **Output**:
   - **Metadata**: Saved in `tcga_data/metadata/<project_id>/<patient_identifier>.json`.
   - **Slides** (if downloaded): Saved in `tcga_data/slides/<project_id>/<patient_identifier>/`.
   - **Per-Project CSV**: Saved as `tcga_data/<project_id>_summary.csv` with:
     - Project ID, total patients, total slides, tissue slides, diagnostic slides, total size (MB), file formats.
     - Per-patient details: patient ID, number of slides, tissue slides, diagnostic slides, size (MB).
   - **All Projects CSV**: Saved as `tcga_data/all_tcga_projects_summary.csv` with one row per project, including project ID, total patients, total slides, tissue slides, diagnostic slides, total size (MB), and file formats.
   - **Log File**: Saved as `tcga_download_log.txt`, capturing all output and errors for debugging.

## Notes
- **Patient IDs**:  If patient IDs appear as "Unknown," it’s due to missing `case_id` or `submitter_id` in the GDC API response. Cross-reference with cBioPortal or contact GDC support for better identifiers.
- **CSV Format**: The `--patient-ids` CSV file must have a `Patient ID` column. Other columns are ignored. Ensure IDs match the GDC API format (e.g., `TCGA-XX-XXXX`).
- **Checksum Verification**: The script skips downloading files that exist with matching MD5 checksums, ensuring no redundant downloads.
- **Retry Logic**: Failed downloads (e.g., due to connection issues) are retried up to 3 times with exponential backoff.
- **Slide Dimensions**: Not available in GDC metadata. Use OpenSlide to extract dimensions from downloaded SVS files. You can use my previous repo [here]([link](https://github.com/EbrahimiAmirHosein/LungHistoNet/tree/amir-experiment/Date%20Prepration))
- **Large Downloads**: Downloading slides (especially with `--download-type both`) may require significant time and storage due to large file sizes.

## Troubleshooting
- **Connection Errors**: Check `tcga_download_log.txt` for details on failed downloads. The script retries up to 3 times for network issues. Ensure a stable internet connection or consider the GDC Data Transfer Tool for bulk downloads.

- **Missing Slides**: If no slides are found for specified patient IDs, a warning is logged, and an empty summary CSV is generated. Verify patient IDs and slide availability on the GDC Data Portal (https://portal.gdc.cancer.gov/projects).
- **Storage Issues**: Monitor disk space when downloading slides. Use `--download-type none` to assess sizes first.

For further assistance, refer to the GDC Data Portal (https://portal.gdc.cancer.gov/) or related resources like https://research.adfoucart.be/tcga-retrieval-gdc-api.