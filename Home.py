import streamlit as st
from typing import Dict, Any
import pandas as pd

def load_css(css_file):
    """Load custom CSS styles."""
    with open(css_file) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def display_overview_metrics(courses: Dict[str, Any]):
    """Display overview metrics for all courses."""
    total_courses = len(courses)
    total_assignments = sum(len(course['todos']) for course in courses.values() if course.get('todos'))
    completed_assignments = sum(
        sum(1 for state in course['todo_states'].values() if state)
        for course in courses.values()
        if course.get('todo_states')
    )

    # Create three columns for metricsx
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Courses", total_courses)
    with col2:
        st.metric("Total Assignments", total_assignments)
    with col3:
        st.metric("Completed Assignments", completed_assignments)

def display_upcoming_deadlines(courses: Dict[str, Any]):
    """Display upcoming deadlines across all courses."""
    all_todos = []
    
    for course_id, course in courses.items():
        if course.get('todos'):
            for todo in course['todos']:
                if not course['todo_states'].get(todo['name'], False):  # Only include uncompleted todos
                    all_todos.append({
                        'Course': course['name'],
                        'Task': todo['name'],
                        'Weight': todo['weight'],
                        'Due Date': todo['due_date']
                    })
    
    if all_todos:
        st.markdown("### 📅 Upcoming Deadlines")
        df = pd.DataFrame(all_todos)
        # Sort by due date if possible, using the format from main.py
        try:
            df['Due Date'] = pd.to_datetime(df['Due Date'], format='%B %d, %Y')
            df = df.sort_values('Due Date')
            # Convert back to the desired format
            df['Due Date'] = df['Due Date'].dt.strftime('%B %d, %Y')
        except:
            pass  # If dates can't be parsed, show unsorted
        st.table(df.set_index('Course'))
    else:
        st.info("No upcoming deadlines found.")

def display_course_progress(courses: Dict[str, Any]):
    """Display progress cards for each course."""
    st.markdown("### 📊 Course Progress")
    
    for course_id, course in courses.items():
        if course.get('file_uploaded') and course.get('analysis_complete'):
            with st.expander(course['name'], expanded=True):
                total_todos = len(course['todos'])
                completed_todos = sum(1 for state in course['todo_states'].values() if state)
                
                if total_todos > 0:
                    progress = completed_todos / total_todos
                    st.progress(progress)
                    st.markdown(f"**{int(progress * 100)}%** complete ({completed_todos}/{total_todos} tasks)")
                else:
                    st.info("No tasks found for this course.")

def main():
    # Replace the emoji with your logo
    logo_path = "assets/logo.png"  # Update with the actual path to your logo file
    logo_width = 60  # Adjust the width as needed

    col1, col2 = st.columns([0.1, 0.9], gap="small")  # Adjust column ratios as needed
    with col1:
        st.image(logo_path, width=logo_width)
    with col2:
        st.markdown("<h1 style='margin: 0; padding: 0; display: inline-block; vertical-align: bottom;'>SyllaBud</h1>", unsafe_allow_html=True)

    st.markdown("##### 🏠 Homepage")
    # Initialize session state if needed
    if 'courses' not in st.session_state:
        st.session_state.courses = {}
    if 'theme_color_name' not in st.session_state:
        st.session_state.theme_color_name = "White"
    
    # Color theme settings in sidebar (always visible)
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
    
    # Load custom CSS
    try:
        load_css('.streamlit/style.css')
    except:
        pass
    
    # Display metrics and information only if there are courses
    if st.session_state.courses:
        st.markdown("---")
        display_overview_metrics(st.session_state.courses)
        
        # Create two columns for the layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            display_upcoming_deadlines(st.session_state.courses)
        
        with col2:
            display_course_progress(st.session_state.courses)
    else:
        # Display welcome message for new users
        # Welcome message
        st.markdown("""
        Welcome to your personal syllabus buddy management dashboard! Here you can:
        - Track all your course schedules in one place
        - Monitor assignment deadlines
        - Keep track of your progress across all courses
        """)

        st.info("👋 Get started by adding your first course in the course tab!")

if __name__ == "__main__":
    main()