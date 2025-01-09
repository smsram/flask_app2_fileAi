from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image
import requests
from io import BytesIO
import PyPDF2
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enables CORS for all routes

# Load environment variables and configure Generative AI API
load_dotenv()
api_key = os.getenv('API_KEY')
if not api_key:
    raise EnvironmentError("API_KEY is not set. Please configure your environment variables.")
genai.configure(api_key=api_key)

# Cache to store file content by URL
file_cache = {}

def process_images_from_urls(image_urls):
    images = []
    for url in image_urls:
        if url in file_cache:
            images.append(file_cache[url])  # Use cached image
        else:
            try:
                response = requests.get(url)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
                file_cache[url] = image  # Cache the image
                images.append(image)
            except Exception as e:
                raise ValueError(f"Error loading image from URL {url}: {str(e)}")
    if not images:
        raise ValueError("No valid images were found from the provided URLs.")
    return images

def process_file_from_url(file_url):
    if file_url in file_cache:
        return file_cache[file_url]  # Use cached file content

    try:
        response = requests.get(file_url)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '')

        if 'application/pdf' in content_type:
            pdf_reader = PyPDF2.PdfReader(BytesIO(response.content))
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text()
            file_cache[file_url] = text  # Cache the text content
            return text
        elif 'text/plain' in content_type:
            text = response.text
            file_cache[file_url] = text  # Cache the text content
            return text
        else:
            raise ValueError("Unsupported file type from URL.")
    except Exception as e:
        raise ValueError(f"Error loading file from URL {file_url}: {str(e)}")

@app.route('/process', methods=['POST'])
def process_request():
    data = request.json
    file_type = data.get("fileType")
    user_prompt = data.get("userPrompt")
    image_urls = data.get("imageUrls", [])
    file_url = data.get("fileUrl")

    try:
        if not file_type or not user_prompt:
            return jsonify({"result": "File type and prompt are required."}), 400

        if file_type == "image":
            if not image_urls:
                return jsonify({"result": "Image URLs are required for image processing."}), 400
            content = process_images_from_urls(image_urls)
        elif file_type == "file":
            if not file_url:
                return jsonify({"result": "File URL is required for file processing."}), 400
            content = process_file_from_url(file_url)
        else:
            return jsonify({"result": "Invalid file type."}), 400

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([user_prompt] + ([content] if file_type == "file" else content))
        return jsonify({"result": response.text})
    except ValueError as e:
        logger.error(f"Input error: {str(e)}")
        return jsonify({"result": f"Input error: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        return jsonify({"result": f"Internal error: {str(e)}"}), 500

if __name__ == "__main__":
    # Set debug to False for production
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit request size to 16 MB
    port = int(os.getenv("PORT", 5000))  # Use the environment variable or default to 5000
    app.run(host="0.0.0.0", port=port, debug=False)
