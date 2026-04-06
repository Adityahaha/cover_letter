import os
from dotenv import load_dotenv
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
from fpdf import FPDF

# LangChain & Gemini Imports
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser



# 1. Load the variables from the .env file into the environment
load_dotenv()

# 2. Access the variable using os.getenv
# Replace "API_KEY" with whatever name you used in your .env file
my_secret_key = os.getenv("GOOGLE_API_KEY")

if my_secret_key:
    print("API Key successfully loaded!")
    # Now you can use my_secret_key in your API requests
else:
    print("Error: API Key not found. Check your .env file.")





# --- IMPORTANT: Paste your actual Gemini API Key here ---
os.environ["GOOGLE_API_KEY"] = my_secret_key

# 1. Initialize the Flask App (This is the line that was missing!)
app = Flask(__name__)

# 2. Initialize Models
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# 3. Route to serve the HTML webpage
@app.route('/')
def index():
    return render_template('index.html')

# 4. Route to generate the cover letter
@app.route('/api/generate', methods=['POST'])
def generate_cover_letter():
    try:
        student_name = request.form.get('student_name')
        company_name = request.form.get('company_name')
        company_address = request.form.get('company_address')
        position = request.form.get('position')
        current_date = request.form.get('current_date') or datetime.now().strftime("%B %d, %Y")
        
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file uploaded'}), 400
            
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            file.save(temp_pdf.name)
            pdf_path = temp_pdf.name

        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        vectorstore = FAISS.from_documents(texts, embeddings)
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})

        prompt_template = """
        You are a professional career advisor. Based on the context extracted from the student's profile and the details below, generate a professional, personalized cover letter.
        Extract student address, email, and other details from the context.

        Inputs:
        - Student Name: {student_name}
        - Company Name: {company_name}
        - Company Address: {company_address}
        - Position: {position}
        - Date: {current_date}

        Context from student profile:
        {context}

        Format the cover letter formally with this structure:

        {student_name}
        [Student Address from profile]
        [City, State, ZIP Code from profile]
        [Email Address from profile]
        {current_date}

        Hiring Manager
        {company_name}
        {company_address}

        Dear Hiring Manager,

        [Personalized body based on context and position]

        Sincerely,
        {student_name}
        """
        prompt = ChatPromptTemplate.from_template(prompt_template)

        rag_chain = (
            {
                "context": (lambda x: x["student_name"]) | retriever | format_docs,
                "student_name": (lambda x: x["student_name"]),
                "company_name": (lambda x: x["company_name"]),
                "company_address": (lambda x: x["company_address"]),
                "position": (lambda x: x["position"]),
                "current_date": (lambda x: x["current_date"])
            }
            | prompt
            | llm
            | StrOutputParser()
        )

        input_data = {
            "student_name": student_name,
            "company_name": company_name,
            "company_address": company_address,
            "position": position,
            "current_date": current_date
        }
        
        response_text = rag_chain.invoke(input_data)
        os.remove(pdf_path)

        return jsonify({'cover_letter': response_text})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

# 5. Route to download the generated text as a PDF
@app.route('/api/download-pdf', methods=['POST'])
def download_pdf():
    try:
        data = request.json
        text = data.get('text', '')
        student_name = data.get('student_name', 'Student')

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)

        for line in text.split("\n"):
            pdf.multi_cell(0, 10, line.encode('latin-1', 'replace').decode('latin-1'))

        clean_name = student_name.replace(" ", "_").replace("/", "_")
        filename = f"Cover_Letter_{clean_name}.pdf"
        
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        pdf.output(file_path)

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return jsonify({'error': str(e)}), 500

# 6. Run the app
if __name__ == '__main__':
    app.run(debug=True)