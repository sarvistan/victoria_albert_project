import requests
import json
import os
import time
import re
from urllib.parse import urljoin

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename).strip()

def download_file(url, filepath):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        print(f"Error downloading file {url}: {e}")
        return False

def extract_image_urls(manifest_data):
    image_urls = []
    if 'sequences' in manifest_data:
        for sequence in manifest_data['sequences']:
            if 'canvases' in sequence:
                for canvas in sequence['canvases']:
                    if 'images' in canvas:
                        for image in canvas['images']:
                            if 'resource' in image and 'service' in image['resource']:
                                service = image['resource']['service']
                                if '@id' in service:
                                    base_url = service['@id']
                                    # Use the IIIF Image API parameters
                                    image_url = f"{base_url}/full/max/0/default.jpg"
                                    image_urls.append(image_url)
    return image_urls

def download_manifest_and_images(manifest_url, output_dir, system_number, title):
    try:
        response = requests.get(manifest_url)
        response.raise_for_status()
        manifest_data = response.json()
        
        # Create a folder for this object
        object_folder = os.path.join(output_dir, system_number)
        os.makedirs(object_folder, exist_ok=True)
        
        # Save the manifest
        sanitized_title = sanitize_filename(title)
        manifest_filename = f"{sanitized_title[:100]}_manifest.json"
        manifest_filepath = os.path.join(object_folder, manifest_filename)
        with open(manifest_filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2)
        print(f"Downloaded manifest: {manifest_filepath}")
        
        # Extract and download images
        image_urls = extract_image_urls(manifest_data)
        for i, image_url in enumerate(image_urls):
            image_filename = f"image_{i+1}.jpg"
            image_filepath = os.path.join(object_folder, image_filename)
            if download_file(image_url, image_filepath):
                print(f"Downloaded image: {image_filepath}")
            else:
                print(f"Failed to download image: {image_url}")
        
        return True
    except requests.RequestException as e:
        print(f"Error processing manifest {manifest_url}: {e}")
        return False

def process_objects(api_url, output_dir):
    objects_processed = 0
    manifests_downloaded = 0
    
    while api_url:
        try:
            print(f"Fetching objects from: {api_url}")
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            if 'records' not in data:
                print(f"Unexpected API response structure: {json.dumps(data, indent=2)}")
                return manifests_downloaded


            records = data['records']
            print(f"Found {len(records)} objects on this page")
            
            for record in records:
                objects_processed += 1
                system_number = record.get('systemNumber', 'Unknown')
                title = record.get('_primaryTitle', 'Untitled')
                print(f"\nProcessing object {objects_processed}: {system_number}")
                print(f"Title: {title}")
                
                manifest_url = record.get('_images', {}).get('_iiif_presentation_url')
                
                if manifest_url:
                    print(f"IIIF Manifest URL: {manifest_url}")
                    if download_manifest_and_images(manifest_url, output_dir, system_number, title):
                        manifests_downloaded += 1
                else:
                    print("No IIIF manifest available for this object")
                
                time.sleep(1)  # Be nice to the server
            
            api_url = data.get('info', {}).get('next')
            
        except requests.RequestException as e:
            print(f"Error processing objects page {api_url}: {e}")
            break
    
    return manifests_downloaded

def main():
    api_url = "https://api.vam.ac.uk/v2/objects/search?q=iran&images=1&page_size=50&iiif=true"
    output_dir = r"C:\Users\agola\Sarvistan\Victoria_Albert"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    total_downloaded = process_objects(api_url, output_dir)
    print(f"\nFinished processing objects.")
    print(f"Downloaded {total_downloaded} IIIF manifests and their associated images from Victoria and Albert Museum.")

if __name__ == "__main__":
    main()
