# TCGA-Histology-Hub
Central hub for TCGA histology data.


## Prerequisites

- **Python 3.6+**: Ensure Python is installed.
- **Required Libraries**: Install the necessary Python libraries using:
  ```bash
  pip install requests
  ```
- **Internet Access**: Required to query the GDC API and download files.
- **Storage Space**: If downloading slides, ensure sufficient disk space (slides can be large, e.g., ~1TB for TCGA-BRCA).

## Script Overview

The script downloads metadata and optionally slide images (SVS format) for selected TCGA projects, organizes them by patient, and generates:
- Per-project CSV summaries (`tcga_data/<project_id>_summary.csv`) with total patients, total slides, tissue slides, diagnostic slides, size (MB), file formats, and per-patient details.
- A single summary CSV (`tcga_data/all_tcga_projects_summary.csv`) aggregating data across all specified projects.

Supported TCGA projects:
- TCGA-BRCA, TCGA-LUAD, TCGA-LUSC, TCGA-OV, TCGA-GBM, TCGA-UCEC, TCGA-COAD, TCGA-PRAD, TCGA-THCA, TCGA-HNSC, TCGA-LIHC

## Usage Instructions


1. **Run the Script**:
   - Use the command line to execute the script with the following arguments:
     - `--download-type`: Specifies what to download:
       - `tissue`: Download tissue slides and metadata.
       - `diagnostic`: Download diagnostic slides and metadata.
       - `both`: Download both tissue and diagnostic slides and metadata.
       - `none`: Download metadata only.
     - `--projects`: Specifies TCGA projects to process:
       - `all`: Process all 11 projects listed above.
       - A single project ID (e.g., `TCGA-BRCA`).
       - Comma-separated project IDs (e.g., `TCGA-BRCA,TCGA-LUAD,TCGA-OV`).

   **Examples**:
   - Download tissue slides and metadata for all projects:
     ```bash
     python gdc-WSI-downloader.py --download-type tissue --projects all
     ```
   - Download diagnostic slides and metadata for TCGA-BRCA only:
     ```bash
     python gdc-WSI-downloader.py --download-type diagnostic --projects TCGA-BRCA
     ```
   - Download both tissue and diagnostic slides for TCGA-BRCA and TCGA-LUAD:
     ```bash
     python gdc-WSI-downloader.py --download-type both --projects TCGA-BRCA,TCGA-LUAD
     ```
   - Download metadata only for all projects:
     ```bash
     python gdc-WSI-downloader.py --download-type none --projects all
     ```

3. **Output**:
   - **Metadata**: Saved in `tcga_data/metadata/<project_id>/<patient_identifier>.json`.
   - **Slides** (if downloaded): Saved in `tcga_data/slides/<project_id>/<patient_identifier>/`.
   - **Per-Project CSV**: Saved as `tcga_data/<project_id>_summary.csv` with:
     - Project ID, total patients, total slides, tissue slides, diagnostic slides, total size (MB), file formats.
     - Per-patient details: patient ID, number of slides, tissue slides, diagnostic slides, size (MB).
   - **All Projects CSV**: Saved as `tcga_data/all_tcga_projects_summary.csv` with one row per project, including project ID, total patients, total slides, tissue slides, diagnostic slides, total size (MB), and file formats.
   - **Console Output**: Displays summaries for each project and notes CSV file creation.

## Notes
- **Patient IDs**: If patient IDs appear as "Unknown," it’s due to missing `case_id` or `submitter_id` in the GDC API response. Cross-reference with cBioPortal or contact GDC support for better identifiers.
- **Slide Dimensions**: Not available in GDC metadata. Use OpenSlide to extract dimensions from downloaded SVS files. You can use my previous repo [here]([link](https://github.com/EbrahimiAmirHosein/LungHistoNet/tree/amir-experiment/Date%20Prepration))
- **Large Downloads**: Downloading slides (especially with `--download-type both`) may require significant time and storage due to large file sizes.

## Troubleshooting
- **API Errors**: Ensure a stable internet connection. Check the GDC API status if requests fail.
- **Missing Slides**: Some projects may have fewer tissue or diagnostic slides. Verify slide availability on the GDC Data Portal (https://portal.gdc.cancer.gov/projects).
- **Storage Issues**: Monitor disk space when downloading slides. Use `--download-type none` to assess sizes first.

For further assistance, refer to the GDC Data Portal (https://portal.gdc.cancer.gov/) or related resources like https://research.adfoucart.be/tcga-retrieval-gdc-api.
