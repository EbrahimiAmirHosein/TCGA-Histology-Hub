import requests
import json
import os
from pathlib import Path
from collections import defaultdict
import csv
import argparse
import hashlib
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pandas as pd

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("tcga_download_log.txt"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

GDC_API_ENDPOINT = "https://api.gdc.cancer.gov"
BASE_DIR = "tcga_data"
METADATA_DIR = os.path.join(BASE_DIR, "metadata")
SLIDES_DIR = os.path.join(BASE_DIR, "slides")

def get_all_projects():
    logger.info("Fetching all TCGA projects with slide images from GDC API")
    url = f"{GDC_API_ENDPOINT}/projects"
    params = {
        "filters": json.dumps({
            "op": "and",
            "content": [
                {"op": "=", "content": {"field": "program.name", "value": "TCGA"}},
                {"op": "in", "content": {"field": "data_categories.data_type", "value": ["Slide Image"]}}
            ]
        }),
        "fields": "project_id",
        "format": "json",
        "size": 1000
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        projects = [hit["project_id"] for hit in response.json()["data"]["hits"]]
        logger.info(f"Found {len(projects)} TCGA projects with slide images: {', '.join(projects)}")
        return projects
    except Exception as e:
        logger.error(f"Failed to fetch TCGA projects: {str(e)}")
        raise

def create_directories(project_id, download_type):
    project_metadata_dir = os.path.join(METADATA_DIR, project_id)
    Path(project_metadata_dir).mkdir(parents=True, exist_ok=True)
    project_slides_dir = None
    if download_type != "none":
        project_slides_dir = os.path.join(SLIDES_DIR, project_id)
        Path(project_slides_dir).mkdir(parents=True, exist_ok=True)
    return project_metadata_dir, project_slides_dir

def get_manifest(project_id):
    logger.info(f"Fetching manifest for {project_id}")
    url = f"{GDC_API_ENDPOINT}/files"
    params = {
        "filters": json.dumps({
            "op": "and",
            "content": [
                {"op": "=", "content": {"field": "cases.project.project_id", "value": project_id}},
                {"op": "=", "content": {"field": "data_category", "value": "Biospecimen"}},
                {"op": "=", "content": {"field": "data_type", "value": "Slide Image"}}
            ]
        }),
        "fields": "file_id,file_name,md5sum,case_id,file_size,data_format,experimental_strategy,cases.submitter_id",
        "format": "json",
        "size": 10000
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def group_by_patient(files, download_type, patient_ids=None):
    patient_slides = defaultdict(list)
    for file in files:
        experimental_strategy = file.get("experimental_strategy", "")
        if download_type == "tissue" and experimental_strategy != "Tissue Slide":
            continue
        if download_type == "diagnostic" and experimental_strategy != "Diagnostic Slide":
            continue
        case_id = file.get("case_id")
        submitter_id = file.get("cases", [{}])[0].get("submitter_id", "Unknown")
        identifier = case_id or submitter_id
        # Filter by patient IDs if provided
        if patient_ids and identifier not in patient_ids:
            continue
        patient_slides[identifier].append(file)
    return patient_slides

def save_metadata(project_id, identifier, slides, project_metadata_dir):
    output_path = os.path.join(project_metadata_dir, f"{identifier}.json")
    with open(output_path, "w") as f:
        json.dump(slides, f, indent=2)
    logger.info(f"Saved metadata for {project_id}, patient {identifier} ({len(slides)} slides)")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    before_sleep=lambda retry_state: logger.warning(f"Retrying download (attempt {retry_state.attempt_number})...")
)
def download_file(project_id, file_id, file_name, identifier, md5sum, project_slides_dir):
    patient_dir = os.path.join(project_slides_dir, identifier)
    Path(patient_dir).mkdir(exist_ok=True)
    output_path = os.path.join(patient_dir, file_name)
    
    # Check if file exists and verify checksum
    if os.path.exists(output_path):
        with open(output_path, "rb") as f:
            file_content = f.read()
            computed_md5 = hashlib.md5(file_content).hexdigest()
        if computed_md5 == md5sum:
            logger.info(f"Skipping {file_name} for {project_id}, patient {identifier}, already exists with matching MD5 checksum")
            return
        else:
            logger.warning(f"Checksum mismatch for {file_name} for {project_id}, patient {identifier}, re-downloading")
    
    # Download file
    logger.info(f"Downloading {file_name} for {project_id}, patient {identifier}")
    url = f"{GDC_API_ENDPOINT}/data/{file_id}"
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    logger.info(f"Downloaded {file_name} for {project_id}, patient {identifier}")

def generate_project_summary_csv(project_id, patient_slides):
    csv_path = os.path.join(BASE_DIR, f"{project_id}_summary.csv")
    total_files = sum(len(slides) for slides in patient_slides.values())
    total_size_bytes = sum(file.get("file_size", 0) for slides in patient_slides.values() for file in slides)
    total_size_mb = total_size_bytes / (1024 * 1024)
    formats = set(file.get("data_format", "Unknown") for slides in patient_slides.values() for file in slides)
    tissue_slides = sum(1 for slides in patient_slides.values() for file in slides if file.get("experimental_strategy") == "Tissue Slide")
    diagnostic_slides = sum(1 for slides in patient_slides.values() for file in slides if file.get("experimental_strategy") == "Diagnostic Slide")
    
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Project", "Total Patients", "Total Slides", "Tissue Slides", "Diagnostic Slides", "Total Size (MB)", "File Formats"])
        writer.writerow([project_id, len(patient_slides), total_files, tissue_slides, diagnostic_slides, f"{total_size_mb:.2f}", ", ".join(formats)])
        writer.writerow([])
        writer.writerow(["Patient ID", "Number of Slides", "Tissue Slides", "Diagnostic Slides", "Size (MB)"])
        for identifier, slides in sorted(patient_slides.items()):
            patient_size_mb = sum(file.get("file_size", 0) for file in slides) / (1024 * 1024)
            patient_tissue = sum(1 for file in slides if file.get("experimental_strategy") == "Tissue Slide")
            patient_diagnostic = sum(1 for file in slides if file.get("experimental_strategy") == "Diagnostic Slide")
            writer.writerow([identifier, len(slides), patient_tissue, patient_diagnostic, f"{patient_size_mb:.2f}"])
    
    logger.info(f"Generated project summary CSV for {project_id}: {csv_path}")
    logger.info(f"Summary for {project_id}:")
    logger.info(f"Total number of patients: {len(patient_slides)}")
    logger.info(f"Total number of slide images: {total_files}")
    logger.info(f"Tissue slides: {tissue_slides}")
    logger.info(f"Diagnostic slides: {diagnostic_slides}")
    logger.info(f"Total size of slides: {total_size_mb:.2f} MB")
    logger.info(f"File formats: {', '.join(formats)}")
    logger.info("Note: Slide dimensions (width, height) are not available in GDC metadata. Download SVS files and use OpenSlide to extract dimensions.")
    
    return {
        "project": project_id,
        "total_patients": len(patient_slides),
        "total_slides": total_files,
        "tissue_slides": tissue_slides,
        "diagnostic_slides": diagnostic_slides,
        "total_size_mb": total_size_mb,
        "file_formats": ", ".join(formats)
    }

def generate_all_projects_summary_csv(project_summaries):
    csv_path = os.path.join(BASE_DIR, "all_tcga_projects_summary.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Project", "Total Patients", "Total Slides", "Tissue Slides", "Diagnostic Slides", "Total Size (MB)", "File Formats"])
        for summary in project_summaries:
            writer.writerow([
                summary["project"],
                summary["total_patients"],
                summary["total_slides"],
                summary["tissue_slides"],
                summary["diagnostic_slides"],
                f"{summary['total_size_mb']:.2f}",
                summary["file_formats"]
            ])
    logger.info(f"Generated all projects summary CSV: {csv_path}")

def download_tcga_slides(download_type="both", projects="all", patient_ids=None):
    if download_type not in ["tissue", "diagnostic", "both", "none"]:
        raise ValueError("download_type must be 'tissue', 'diagnostic', 'both', or 'none'")
    
    # Fetch all TCGA projects with slide images
    all_projects = get_all_projects()
    
    if projects.lower() == "all":
        project_list = all_projects
    else:
        project_list = [p.strip() for p in projects.split(",")]
        invalid_projects = [p for p in project_list if p not in all_projects]
        if invalid_projects:
            raise ValueError(f"Invalid project(s): {', '.join(invalid_projects)}. Available projects: {', '.join(all_projects)}")
    
    # Process patient_ids
    if patient_ids:
        if patient_ids.endswith(".csv"):
            try:
                df = pd.read_csv(patient_ids)
                if "Patient ID" not in df.columns:
                    raise ValueError(f"CSV file {patient_ids} must contain a 'Patient ID' column")
                patient_id_list = df["Patient ID"].dropna().astype(str).str.strip().tolist()
                logger.info(f"Loaded {len(patient_id_list)} patient IDs from CSV file: {patient_ids}")
            except Exception as e:
                raise ValueError(f"Failed to read CSV file {patient_ids}: {str(e)}")
        else:
            patient_id_list = [pid.strip() for pid in patient_ids.split(",")]
            logger.info(f"Loaded {len(patient_id_list)} patient IDs from command-line input")
    else:
        patient_id_list = None
        logger.info("No patient IDs specified, processing all patients")
    
    project_summaries = []
    for project_id in project_list:
        logger.info(f"Processing {project_id}...")
        project_metadata_dir, project_slides_dir = create_directories(project_id, download_type)
        try:
            manifest = get_manifest(project_id)
            files = manifest["data"]["hits"]
            patient_slides = group_by_patient(files, download_type if download_type != "none" else "both", patient_id_list)
            
            if not patient_slides:
                logger.warning(f"No matching slides found for {project_id} with specified patient IDs")
            
            for identifier, slides in patient_slides.items():
                save_metadata(project_id, identifier, slides, project_metadata_dir)
                if download_type != "none":
                    for file in slides:
                        if (download_type == "tissue" and file.get("experimental_strategy") != "Tissue Slide") or \
                           (download_type == "diagnostic" and file.get("experimental_strategy") != "Diagnostic Slide"):
                            continue
                        file_id = file["file_id"]
                        file_name = file["file_name"]
                        md5sum = file["md5sum"]
                        try:
                            download_file(project_id, file_id, file_name, identifier, md5sum, project_slides_dir)
                        except Exception as e:
                            logger.error(f"Failed to download {file_name} for {project_id}, patient {identifier}: {str(e)}")
                            continue
            
            project_summary = generate_project_summary_csv(project_id, patient_slides)
            project_summaries.append(project_summary)
        
        except Exception as e:
            logger.error(f"Failed to process {project_id}: {str(e)}")
            continue
    
    generate_all_projects_summary_csv(project_summaries)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download TCGA metadata and slides by type, projects, and patient IDs.")
    parser.add_argument("--download-type", choices=["tissue", "diagnostic", "both", "none"], default="both",
                        help="Type of slides to download: 'tissue', 'diagnostic', 'both', or 'none' for metadata only")
    parser.add_argument("--projects", default="all",
                        help="Comma-separated TCGA project IDs (e.g., TCGA-BRCA,TCGA-LUAD) or 'all' for all available projects with slide images")
    parser.add_argument("--patient-ids", default=None,
                        help="Path to a CSV file with 'Patient ID' column or comma-separated patient IDs (e.g., TCGA-XX-XXXX,TCGA-YY-YYYY)")
    args = parser.parse_args()
    
    download_tcga_slides(args.download_type, args.projects, args.patient_ids)