import os
import io
import docx
import uuid
import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from typing import Optional
import pandas as pd


# Must be the first Streamlit command
st.set_page_config(page_title="📚 Syllabus Analyzer")


# Load environment variables
load_dotenv(dotenv_path='.env')


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def load_css(css_file):
    with open(css_file) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Use it in your app
load_css('.streamlit/style.css')



def initialize_session_state():
    """Initialize session state variables for both course management and todo tracking."""
    if 'courses' not in st.session_state:
        st.session_state.courses = {}  # Dict to store course data
   
    # Initialize course-specific states if they don't exist
    for course_id in st.session_state.courses:
        if 'todos' not in st.session_state.courses[course_id]:
            st.session_state.courses[course_id]['todos'] = []
        if 'todo_states' not in st.session_state.courses[course_id]:
            st.session_state.courses[course_id]['todo_states'] = {}
        if 'weekly_schedule' not in st.session_state.courses[course_id]:
            st.session_state.courses[course_id]['weekly_schedule'] = []
        if 'analysis_complete' not in st.session_state.courses[course_id]:
            st.session_state.courses[course_id]['analysis_complete'] = False


def read_pdf(file) -> str:
    """Read and extract text from a PDF file."""
    pdf_reader = PdfReader(io.BytesIO(file.read()))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


def read_docx(file) -> str:
    """Read and extract text from a DOCX file."""
    doc = docx.Document(io.BytesIO(file.read()))
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


def analyze_with_openai(text: str) -> Optional[str]:
    """Analyze document text using OpenAI API."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{

               "role": "user",
               "content": f"""
               You are given a course syllabus document. Your task is to extract and display the following information in the sections with the exact formatting described below:

                # Course Information
                Extract the course code and name. Common formats include "CS 1234", "COMPSCI 1234", or similar.
                Return it in this format:
                Course: [course code] - [course name]

               **Weekly Schedule**
               Create a neatly formatted table that lists the course content, assignments week by week. If certain types of activities (e.g., labs) do not apply to this course, omit the column for those activities. Here is the required format for the table:


               | **Week** | **Course Content**       |
               |----------|--------------------------|
               | Week 1   | Summary of Week 1 content|
               | Week 2   | Summary of Week 2 content|
               | Week 3   | Summary of Week 3 content|
               | ...      | ...                      |


               **To-do List**
               Extract and list **all deliverables** (assignments, tests, midterms, final exams, projects, etc.) in the order they appear in the syllabus. For each deliverable, include:
              
               - **The exact name of the deliverable** (e.g., "Assignment 1", "Midterm Exam").
               - **The percentage of the final course grade** (if available).
               - **The due date** (if specified).


               If a due date or percentage is not provided in the syllabus, leave that field blank. Here is the required format for the table:


               | **Name**               | **% of Course Grade** | **Due Date**       |
               |------------------------|-----------------------|--------------------|
               | Assignment 1           | 10%                   | January 15, 2025   |
               | Midterm Exam           | 25%                   | February 10, 2025  |
               | Final Project          | 30%                   | April 5, 2025      |
               | ...                    | ...                   | ...                |


               **Important Notes**:
               - Use the exact names and details from the syllabus without modifying them.
               - After extracting all deliverables, organize the order of the  to display so that it is by date, from Jan to Dec in a calender year
               - If a deliverable does not have a due date or percentage, fill the cell with the words "N/A".
               - Never include ..., this should always be filled by the content of the syllabus
               - Think about the weightings, sometimes assignments will be split up. Always keep in mind that the total weighting should add up to 100

                Here is the document text:
                {text}
                """
            }],
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error with OpenAI API: {str(e)}")
        return None


def update_todo_state(course_id: str, todo_name: str, state: bool):
    """Update the state of a todo item for a specific course."""
    st.session_state.courses[course_id]['todo_states'][todo_name] = state




def extract_course_name(analysis_text: str) -> str:
    """Extract course code/name from the syllabus analysis."""
    try:
        sections = analysis_text.split('#')
        for section in sections:
            if 'Course Information' in section:
                lines = section.split('\n')
                for line in lines:
                    if line.strip().startswith('Course:'):
                        return line.replace('Course:', '').strip()
        return "New Course"
    except:
        return "New Course"


def parse_todo_list(analysis: str) -> list:
    """Parse the todo list from the analysis text."""
    try:
        parts = analysis.split('**To-do List**')
        if len(parts) < 2:
            parts = analysis.split('To-do List')
       
        if len(parts) < 2:
            return []


        todo_section = parts[1]
        lines = [line.strip() for line in todo_section.split('\n')]
        rows = [
            row for row in lines
            if row and not row.startswith('|-') and not row.startswith('| **') and '|' in row
        ]
       
        todos = []
        for row in rows:
            cells = [cell.strip() for cell in row.split('|')]
            cells = [cell for cell in cells if cell]
           
            if len(cells) >= 3:
                name = cells[0]
                weight = cells[1] if len(cells) > 1 else "N/A"
                due_date = cells[2] if len(cells) > 2 else "N/A"
               
                if name and name not in ['Name', '**Name**']:
                    todos.append({
                        'name': name,
                        'weight': weight,
                        'due_date': due_date
                    })
        return todos
    except Exception as e:
        st.error(f"Error parsing todo list: {str(e)}")
        return []


def parse_weekly_schedule(analysis: str) -> list:
    """Parse the weekly schedule from the analysis text, ensuring no evaluation rows."""
    try:
        # Split by Weekly Schedule header
        parts = analysis.split('**Weekly Schedule**')
        if len(parts) < 2:
            parts = analysis.split('Weekly Schedule')
       
        if len(parts) < 2:
            return []
           
        # Get the section between Weekly Schedule and To-do List
        schedule_section = parts[1].split('**To-do List**')[0]
       
        # Split into lines and clean them
        lines = [line.strip() for line in schedule_section.split('\n')]
       
        # Filter out empty lines, separator lines, rows containing percentage symbols, or "Evaluation" markers
        rows = [
            row for row in lines
            if row and not row.startswith('|-') and not row.startswith('| **') and '|' in row
            and '%' not in row  # Filter out rows containing '%' (typically assignments/test marks)
            and not any(keyword in row.lower() for keyword in ["exam", "assignment", "project"])  # Avoid rows with evaluation keywords
        ]
       
        # Parse each row into a dictionary
        schedule = []
        for row in rows:
            cells = [cell.strip() for cell in row.split('|')]
            cells = [cell for cell in cells if cell]
           
            if len(cells) >= 2:
                week = cells[0]
                content = cells[1]
               
                if week and week not in ['Week', '**Week**']:
                    schedule.append({
                        'week': week,
                        'content': content
                    })
       
        return schedule
    except Exception as e:
        st.error(f"Error parsing weekly schedule: {str(e)}")
        return []




def create_text_menu(course_id):
    """Create a row of text-based options below the course title."""
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Rename Page", key=f"rename_{course_id}"):
            st.session_state[f"renaming_{course_id}"] = True
            st.rerun()
   
    with col2:
        if st.button("Reupload Syllabus", key=f"reupload_{course_id}"):
            st.session_state.courses[course_id]['file_uploaded'] = False
            st.rerun()
   
    with col3:
        if st.button("Delete Page", key=f"delete_{course_id}"):
            del st.session_state.courses[course_id]
            st.rerun()






def course_tab(course_id):
    """Display the course tab with all functionality."""
    course_data = st.session_state.courses[course_id]
   
    # Header section with course name and text menu
    if course_data.get('file_uploaded'):
        if st.session_state.get(f"renaming_{course_id}", False):
            # Rename input with confirm button
            container = st.container()
            with container:
                col_input, col_confirm = st.columns([0.95, 0.05])
                with col_input:
                    new_name = st.text_input(
                        "",
                        value=course_data['name'],
                        key=f"rename_input_{course_id}",
                        label_visibility="collapsed"
                    )
                with col_confirm:
                    if st.button("✓", key=f"confirm_rename_{course_id}"):
                        course_data['name'] = new_name
                        st.session_state[f"renaming_{course_id}"] = False
                        st.rerun()
        else:
            st.header(course_data['name'])
       
        # Add text menu options below the header
        create_text_menu(course_id)


    # Upload section
    if not course_data.get('file_uploaded'):
        uploaded_file = st.file_uploader(
            "Upload course syllabus",
            type=['pdf', 'docx'],
            key=f"file_{course_id}"
        )


        if uploaded_file is not None:
            with st.spinner('Processing syllabus...'):
                try:
                    # Read the file
                    if uploaded_file.type == "application/pdf":
                        text = read_pdf(uploaded_file)
                    else:
                        text = read_docx(uploaded_file)
                   
                    # Analyze with OpenAI
                    analysis = analyze_with_openai(text)
                    if analysis:
                        # Extract course name and parse components
                        course_name = extract_course_name(analysis)
                        course_data['name'] = course_name
                        course_data['syllabus_text'] = text
                        course_data['analysis'] = analysis
                        course_data['todos'] = parse_todo_list(analysis)
                        course_data['weekly_schedule'] = parse_weekly_schedule(analysis)
                        course_data['file_uploaded'] = True
                        course_data['analysis_complete'] = True
                       
                        # Initialize todo states
                        for todo in course_data['todos']:
                            if todo['name'] not in course_data['todo_states']:
                                course_data['todo_states'][todo['name']] = False
                       
                        st.success("Syllabus processed successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error processing document: {str(e)}")
   
    # After file processing, add display sections:
    if course_data.get('file_uploaded') and course_data.get('analysis_complete'):
        # Display weekly schedule
        if course_data['weekly_schedule']:
            st.markdown("### Weekly Schedule")
           
            # Convert schedule data to table format
            table_data = {
                "Week": [],
                "Course Content": []
            }
            for week in course_data['weekly_schedule']:
                table_data["Week"].append(week['week'])
                table_data["Course Content"].append(week['content'])
           
            # Display as table
            df = pd.DataFrame(table_data)
            st.table(df.set_index('Week'))


        # Display interactive todo list
        if course_data['todos']:
            st.markdown("### Methods of Evaluation")


            # Create columns for checkboxes and table
            col1, col2 = st.columns([0.1, 0.9])


            with col1:
                # Create checkboxes with unique keys
                for index, todo in enumerate(course_data['todos']):
                    unique_key = f"checkbox_{course_id}_{index}"
                    st.checkbox(
                        "",
                        key=unique_key,
                        value=course_data['todo_states'].get(todo['name'], False),
                        on_change=update_todo_state,
                        args=(course_id, todo['name'], not course_data['todo_states'].get(todo['name'], False))
                    )


           
            with col2:
                # Create todo table
                todo_data = {
                    "Task": [],
                    "Weight": [],
                    "Due Date": []
                }
                for todo in course_data['todos']:
                    todo_data["Task"].append(todo['name'])
                    todo_data["Weight"].append(todo['weight'])
                    todo_data["Due Date"].append(todo['due_date'])
               
                # Display as table
                df = pd.DataFrame(todo_data)
                st.table(df.set_index('Task'))




def add_custom_styling():
    st.markdown("""
        <style>
        /* Menu button (≡) styling */
        .stButton > button:first-child {
            background: none !important;
            border: none !important;
            padding: 0 !important;
            font-size: 14px !important;  /* Decreased font size */
            line-height: 1 !important;
            color: #555 !important;  /* Lighter color for buttons */
            position: relative !important;
            width: 100% !important;  /* Ensure button takes full width of column */
            margin: 5px 0 !important;  /* Add margin between buttons */
        }
       
        .stButton > button:first-child:hover {
            background-color: #f0f0f0 !important;  /* Hover effect for buttons */
        }
       
        /* Title container customization */
        .css-1v3fvcr {
            font-size: 24px !important;  /* Title font size */
        }
       
        /* Remove default margins and padding from columns */
        .stColumn > div {
            margin: 0 !important;
            padding: 0 !important;
        }
       
        /* Add spacing between title and button column */
        .css-1ekg3b4 {
            padding-top: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

def add_theme_picker():
    """Add theme picker to sidebar and apply selected theme."""
    # Initialize theme color in session state if it doesn't exist
    if 'theme_color_name' not in st.session_state:
        st.session_state.theme_color_name = "White"
        
    # Color theme settings
    color_options = {
        "White": "#FFFFFF",          # Pure white
        "Pink": "#fff6f6",           # Softer, lighter pink
        "Orange": "#fff7ef",         # Even more muted peach/orange
        "Yellow": "#fffff1",         # Lighter, softer yellow
        "Green": "#f7fff3",          # Softer, lighter sage green
        "Blue": "#f5f9ff",           # More muted sky blue
        "Purple": "#f8f4ff",         # Lighter lavender
    }

    with st.sidebar:
        selected_color = st.selectbox(
            "Theme Color",
            options=list(color_options.keys()),
            index=list(color_options.keys()).index(st.session_state.theme_color_name)
        )
        st.session_state.theme_color_name = selected_color

    background_color = color_options[selected_color]

    # Apply the selected background color to the entire page
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {background_color};
            background-attachment: fixed;
            background-size: cover;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


def main():

    # Replace the emoji with your logo
    logo_path = "assets/logo.png"  # Update with the actual path to your logo file
    logo_width = 60  # Adjust the width as needed

    col1, col2 = st.columns([0.1, 0.9], gap="small")  # Adjust column ratios as needed
    with col1:
        st.image(logo_path, width=logo_width)
    with col2:
        st.markdown("<h1 style='margin: 0; padding: 0; display: inline-block; vertical-align: bottom;'>SyllaBud</h1>", unsafe_allow_html=True)

    st.markdown("##### 📚 Courses")
   
    add_theme_picker() 
    initialize_session_state()


    if not os.getenv('OPENAI_API_KEY'):
        st.error("Please set your OPENAI_API_KEY environment variable")
        st.stop()


    # Add Course button
    if st.button("+ Add Course"):
        new_course_id = str(uuid.uuid4())
        new_course = {
            'name': 'New Course',
            'syllabus_text': None,
            'analysis': None,
            'file_uploaded': False,
            'todos': [],
            'todo_states': {},
            'weekly_schedule': [],
            'analysis_complete': False
        }
       
        # Add new course to the beginning
        new_courses = {new_course_id: new_course}
        new_courses.update(st.session_state.courses)
        st.session_state.courses = new_courses


    # Display courses in tabs
    if st.session_state.courses:
        valid_courses = {
            cid: data for cid, data in st.session_state.courses.items()
            if data is not None
        }
       
        if valid_courses:
            courses = {cid: str(data['name']) for cid, data in valid_courses.items()}
            tab_names = list(courses.values())
            tabs = st.tabs(tab_names)
           
            for (course_id, _), tab in zip(courses.items(), tabs):
                with tab:
                    course_tab(course_id)
        else:
            st.info("Add a course to get started!")
    else:
        st.info("Add a course to get started!")


if __name__ == "__main__":
    main()




