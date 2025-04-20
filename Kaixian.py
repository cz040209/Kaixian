from streamlit_chat import message
import requests
import streamlit as st
from datetime import datetime
from gtts import gTTS  # Import gtts for text-to-speech
import os
import torch
from PIL import Image
import json
from io import BytesIO
import openai
import pytz
import time

def set_background(image_url):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{image_url}");
            background-size: cover;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

background_image_url = "https://i.pinimg.com/originals/6b/a1/74/6ba174bf48e9b6dc8d8bd19d13c9caa9.gif"

st.markdown("""
    <style>
        /* Existing CSS */
        .css-1d391kg {
            background-color: #1c1f24;
            color: white;
            font-family: 'Arial', sans-serif;
        }
        .css-1v0m2ju {
            background-color: #282c34;
        }
        .css-13ya6yb {
            background-color: #61dafb;
            border-radius: 5px;
            padding: 10px 20px;
            color: white;
            font-size: 16px;
            font-weight: bold;
        }
        .css-10trblm {
            font-size: 18px;
            font-weight: bold;
            color: #282c34;
        }
        .css-3t9iqy {
            color: #61dafb;
            font-size: 20px;
        }
        .Emøtica-title {
            font-family: 'Arial', sans-serif;
            font-size: 60px;
            font-weight: bold;
            color: #61dafb;
            text-align: center;
            margin-top: 50px;
            margin-bottom: 30px;
            position: fixed;
            top: 60px;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            z-index: 1000;
            background-color: rgba(28, 31, 36, 0.8);
            padding: 10px 0;
        }
        /* CSS for the fixed bottom icons */
        .fixed-bottom-icons {
            position: fixed !important;
            bottom: 80px !important; /* Increased bottom value */
            left: 50% !important;
            transform: translateX(-50%) !important;
            z-index: 1001 !important;
            display: flex !important;
            gap: 20px !important; /* Adjust spacing between icons */
        }
        .fixed-bottom-icons button[data-testid="stButton"] {
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 20px;
            border: none;
            background-color: #61dafb; /* Set a default background color */
            color: white;
            cursor: pointer;
        }
        /* Specific color for the voice call button */
        .fixed-bottom-icons button[data-testid="stButton"][key="call_button_voice"] {
            background-color: #ADD8E6;
        }
        /* Specific color for the video call button */
        .fixed-bottom-icons button[data-testid="stButton"][key="call_button_video"] {
            background-color: #90EE90;
        }
    </style>
""", unsafe_allow_html=True)

# Emøtica Title
st.markdown('<h1 class="Emøtica-title">Emøtica</h1>', unsafe_allow_html=True)

# Initialize session state for authentication
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None

# Dummy user data (replace with a real database)
users = {"testuser": {"password": "testpass"}}

def login(username, password):
    if username in users and users[username]["password"] == password:
        st.session_state["authentication_status"] = True
        st.session_state["username"] = username
        st.sidebar.success(f"Logged in as {username}")
        return True
    else:
        st.error("Invalid username or password")
        return False

def register(username, password):
    if username in users:
        st.error("Username already exists")
        return False
    else:
        users[username] = {"password": password}
        st.success("Registration successful. You can now log in.")
        return True

def logout():
    st.session_state["authentication_status"] = False
    st.session_state["username"] = None
    st.sidebar.info("Logged out")

def login_page():
    st.markdown(
        """
        <style>
        .stApp {
            background-image: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        login(username, password)
    st.markdown("Don't have an account? [Register here](register)")

def register_page():
    st.markdown(
        """
        <style>
        .stApp {
            background-image: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.subheader("Register")
    username = st.text_input("New Username")
    password = st.text_input("New Password", type="password")
    password_confirm = st.text_input("Confirm Password", type="password")
    if st.button("Register"):
        if password == password_confirm:
            register(username, password)
        else:
            st.error("Passwords do not match")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Chat", "Login", "Register"])

if page == "Login":
    login_page()
elif page == "Register":
    register_page()
elif page == "Chat":
    set_background(background_image_url)
    # Initialize session state variables at the beginning of the Chat page logic
    if "history" not in st.session_state:
        st.session_state.history = []
    if "past_conversations" not in st.session_state:
        st.session_state.past_conversations = []
    if "current_conversation_index" not in st.session_state:
        st.session_state.current_conversation_index = -1  # -1 indicates no specific past conversation is active
    if 'content' not in st.session_state:
        st.session_state['content'] = ''
    if 'generated_summary' not in st.session_state:
        st.session_state['generated_summary'] = ''

    # Create a container for the call icons at the bottom only on the Chat page
    call_icon_container = st.container()
    with call_icon_container:
        st.markdown("""
            <div class="fixed-bottom-icons">
                <button data-testid="stButton" key="call_button_voice" title="Initiate a Voice Call">📞</button>
                <button data-testid="stButton" key="call_button_video" title="Initiate a Video Call">📹</button>
            </div>
        """, unsafe_allow_html=True)

    if st.session_state["authentication_status"]:
        # Set up API Key directly
        api_key = "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"

        # Base URL and headers for Groq API
        base_url = "https://api.groq.com/openai/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Available models
        available_models = {
            "Mixtral 8x7b": "mixtral-8x7b-32768",
            "Llama-3.1-8b-instant": "llama-3.1-8b-instant",
            "gemma2-9b-it": "gemma2-9b-it",
        }


        # Function to Translate Text Using the Selected Model
        def translate_text(text, target_language, model_id):
            url = f"{base_url}/chat/completions"
            data = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": f"Translate the following text into {target_language}."},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.7,
                "max_tokens": 300,
                "top_p": 0.9
            }

            try:
                response = requests.post(url, headers=headers, json=data)
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                else:
                    return f"Translation error: {response.status_code}"
            except requests.exceptions.RequestException as e:
                return f"An error occurred during translation: {e}"


        # Sidebar for model selection
        st.sidebar.header("Model Selection")
        selected_model = st.sidebar.selectbox("Choose a model:", list(available_models.keys()))
        selected_model_id = available_models[selected_model]

        # Display conversation history
        for interaction in st.session_state.history:
            st.chat_message("user").write(f"[{interaction['time']}] {interaction['question']}")
            st.chat_message("assistant").write(interaction["response"] or "Thinking...")

        # Get user input based on button clicks
        user_input = None
        if st.session_state.get("call_button_voice"):
            user_input = "Initiate a voice call."  # You can customize this message
        elif st.session_state.get("call_button_video"):
            user_input = "Initiate a video call."  # You can customize this message

        if user_input:
            # Set the timezone to Malaysia for the timestamp
            malaysia_tz = pytz.timezone("Asia/Kuala_Lumpur")
            current_time = datetime.now(malaysia_tz).strftime("%Y-%m-%d %H:%M:%S")

            # Prepare the interaction data for history tracking
            interaction = {
                "time": current_time,
                "input_method": "call_button",
                "question": user_input,
                "response": "",
                "content_preview": st.session_state['content'][:100] if st.session_state['content'] else "No content available"
            }

            # Add the user question to the history
            st.session_state.history.append(interaction)

            # Display the user's input immediately
            st.chat_message("user").write(user_input)

            # Display "Thinking..." for assistant response
            st.chat_message("assistant").write("Thinking...")

            # Track start time for response calculation
            start_time = time.time()

            # Prepare the data for API call
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ]
            if st.session_state['content']:
                messages.insert(1, {"role": "system", "content": f"Use the following content: {st.session_state['content']}"})

            data = {
                "model": selected_model_id,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 200,
                "top_p": 0.9
            }

            try:
                # Send the request to the API
                response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data)

                # Track end time for response calculation
                end_time = time.time()
                response_time = end_time - start_time

                if response.status_code == 200:
                    result = response.json()
                    answer = result['choices'][0]['message']['content']

                    # Update the latest interaction with the model's response
                    st.session_state.history[-1]["response"] = answer

                    # Display the assistant's response
                    st.chat_message("assistant").write(answer)

                    # Display the response time
                    st.write(f"Response Time: {response_time:.2f} seconds")

                else:
                    st.chat_message("assistant").write(f"Error {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                st.chat_message("assistant").write(f"An error occurred: {e}")

        # Display the interaction history in the sidebar with clickable expanders
        st.sidebar.header("Interaction History")

        # Add the "Clear History" button to clear all past conversations
        if st.sidebar.button("Clear History"):
            # Clear the archive of past conversations
            st.session_state.past_conversations = []
            st.session_state.history = []
            st.session_state.current_conversation_index = -1
            st.sidebar.success("All past conversations have been cleared!")
            st.rerun()  # Refresh the app to reflect the changes

        # Display the current chat history if available
        if st.session_state.history:
            st.sidebar.write("**Current Chat:**")
            with st.sidebar.expander("Full Conversation"):
                for idx, interaction in enumerate(st.session_state.history):
                    st.markdown(f"**Interaction {idx+1}:**")
                    st.markdown(f"- **Time:** {interaction['time']}")
                    st.markdown(f"- **Question:** {interaction['question']}")
                    st.markdown(f"- **Response:** {interaction['response']}")


        # Display the past conversations and allow users to navigate between them
        if st.session_state.past_conversations:
            st.sidebar.write("**Past Conversations:**")
            for conv_idx, conversation in enumerate(st.session_state.past_conversations):
                with st.sidebar.expander(f"Conversation {conv_idx+1}"):
                    for idx, interaction in enumerate(conversation):
                        # Display the interaction time along with the question and response
                        st.markdown(f"**Interaction {idx+1}:**")
                        st.markdown(f"- **Time:** {interaction['time']}")
                        st.markdown(f"- **Question:** {interaction['question']}")
                        st.markdown(f"- **Response:** {interaction['response']}")

                    # Add a button to switch to this past conversation
                    if st.sidebar.button(f"Switch to Conversation {conv_idx+1}", key=f"switch_{conv_idx}"):
                        # Save the current history to past conversations
                        if st.session_state.current_conversation_index == -1 and st.session_state.history:
                            st.session_state.past_conversations.append(st.session_state.history)

                        # Load the selected conversation into the current history
                        st.session_state.history = conversation
                        st.session_state.current_conversation_index = conv_idx
                        st.sidebar.success(f"Switched to Conversation {conv_idx+1}")
                        st.rerun()  # Refresh the app to reflect the changes

        else:
            st.sidebar.write("No past conversations yet.")

        # Add the "Start New Chat" button to reset only the current interaction history
        if st.sidebar.button("Start a New Chat"):
            if st.session_state.history:
                # Save the current history to past conversations
                if st.session_state.current_conversation_index == -1:
                    st.session_state.past_conversations.append(st.session_state.history)
                else:
                    # Update the active conversation in past conversations
                    st.session_state.past_conversations[st.session_state.current_conversation_index] = st.session_state.history

            # Clear the current history for a new chat session
            st.session_state.history = []
            st.session_state.current_conversation_index = -1
            st.session_state['content'] = ''
            st.session_state['generated_summary'] = ''
            st.sidebar.success("New chat started!")
            st.rerun()  # Refresh the app to reflect the changes

        # Add functionality to save the entire conversation
        def append_to_history(question, response):
            """Append a question and response to the current conversation history."""
            st.session_state.history.append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "question": question,
                "response": response
            })


        # Function to ask a question about the content
        def ask_question(question):
            if question and selected_model_id:
                # Track start time for question response
                start_time = time.time()

                # Prepare the request payload for the question
                url = f"{base_url}/chat/completions"
                data = {
                    "model": selected_model_id,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant. Use the following content to answer the user's questions."},
                        {"role": "system", "content": st.session_state['content']},  # Use the current content as context
                        {"role": "user", "content": question}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 200,
                    "top_p": 0.9
                }

                try:
                    # Send request to the API
                    response = requests.post(url, headers=headers, json=data)

                    # Track end time for question response
                    end_time = time.time()
                    response_time = end_time - start_time

                    if response.status_code == 200:
                        result = response.json()
                        answer = result['choices'][0]['message']['content']

                        # Track the interaction history
                        malaysia_tz = pytz.timezone("Asia/Kuala_Lumpur")
                        current_time = datetime.now(malaysia_tz).strftime("%Y-%m-%d %H:%M:%S")

                        # Only store interactions with a valid question and response
                        if answer and question:
                            interaction = {
                                "time": current_time,
                                "question": question,
                                "response": answer,
                                "content_preview": st.session_state['content'][:100] if st.session_state['content'] else "No content available",
                                "response_time": f"{response_time:.2f} seconds"  # Store the response time
                            }
                            if "history" not in st.session_state:
                                st.session_state.history = []
                            st.session_state.history.append(interaction)  # Add a new entry only when there's a valid response

                            # Display the answer along with the response time
                            st.write(f"Answer: {answer}")
                            st.write(f"Question Response Time: {response_time:.2f} seconds")

                            # Update content with the latest answer
                            st.session_state['content'] += f"\n{question}: {answer}"

                    else:
                        st.write(f"Error {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as e:
                    st.write(f"An error occurred: {e}")


        # Sidebar for interaction history
        if "history" not in st.session_state:
            st.session_state.history = []

        # Initialize content variable
        content = ""



        # Sidebar for interaction history (should come early)
        if "history" not in st.session_state:
            st.session_state.history = []
        content = ""

        # Display conversation history
        for interaction in st.session_state.history:
            st.chat_message("user").write(f"[{interaction['time']}] {interaction['question']}")
            st.chat_message("assistant").write(interaction["response"] or "Thinking...")

        # Get user input based on button clicks
        user_input = None
        if st.session_state.get("call_button_voice"):
            user_input = "Initiate a voice call."  # You can customize this message
        elif st.session_state.get("call_button_video"):
            user_input = "Initiate a video call."  # You can customize this message

        if user_input:
            # Set the timezone to Malaysia for the timestamp
            malaysia_tz = pytz.timezone("Asia/Kuala_Lumpur")
            current_time = datetime.now(malaysia_tz).strftime("%Y-%m-%d %H:%M:%S")

            # Prepare the interaction data for history tracking
            interaction = {
                "time": current_time,
                "input_method": "call_button",
                "question": user_input,
                "response": "",
                "content_preview": content[:100] if content else "No content available"
            }

            # Add the user question to the history
            st.session_state.history.append(interaction)

            # Display the user's input immediately
            st.chat_message("user").write(user_input)

            # Display "Thinking..." for assistant response
            st.chat_message("assistant").write("Thinking...")

            # Track start time for response calculation
            start_time = time.time()

            # Prepare the data for API call
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ]
            if content:
                messages.insert(1, {"role": "system", "content": f"Use the following content: {content}"})

            data = {
                "model": selected_model_id,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 200,
                "top_p": 0.9
            }

            try:
                # Send the request to the API
                response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data)

                # Track end time for response calculation
                end_time = time.time()
                response_time = end_time - start_time

                if response.status_code == 200:
                    result = response.json()
                    answer = result['choices'][0]['message']['content']

                    # Update the latest interaction with the model's response
                    st.session_state.history[-1]["response"] = answer

                    # Display the assistant's response
                    st.chat_message("assistant").write(answer)

                    # Display the response time
                    st.write(f"Response Time: {response_time:.2f} seconds")

                else:
                    st.chat_message("assistant").write(f"Error {response.status_code}: {response.text}")
            except requests.exceptions.RequestException as e:
                st.chat_message("assistant").write(f"An error occurred: {e}")


        # Initialize session state variables if not already set
        if "history" not in st.session_state:
            st.session_state.history


        # Initialize session state variables if not already set
        if "history" not in st.session_state:
            st.session_state.history = []

        if "past_conversations" not in st.session_state:
            st.session_state.past_conversations = []

        if "current_conversation_index" not in st.session_state:
            st.session_state.current_conversation_index = -1  # -1 indicates no specific past conversation is active

        # Display the interaction history in the sidebar with clickable expanders
        st.sidebar.header("Interaction History")

# Add the "Clear History" button to clear all past conversations
if st.sidebar.button("Clear History"):
    # Clear the archive of past conversations
    st.session_state.past_conversations = []
    st.session_state.history = []
    st.session_state.current_conversation_index = -1
    st.sidebar.success("All past conversations have been cleared!")
    st.rerun()  # Refresh the app to reflect the changes

# Display the current chat history if available
if st.session_state.history:
    st.sidebar.write("**Current Chat:**")
    with st.sidebar.expander("Full Conversation"):
        for idx, interaction in enumerate(st.session_state.history):
            st.markdown(f"**Interaction {idx+1}:**")
            st.markdown(f"- **Time:** {interaction['time']}")
            st.markdown(f"- **Question:** {interaction['question']}")
            st.markdown(f"- **Response:** {interaction['response']}")


# Display the past conversations and allow users to navigate between them
if st.session_state.past_conversations:
    st.sidebar.write("**Past Conversations:**")
    for conv_idx, conversation in enumerate(st.session_state.past_conversations):
        with st.sidebar.expander(f"Conversation {conv_idx+1}"):
            for idx, interaction in enumerate(conversation):
                # Display the interaction time along with the question and response
                st.markdown(f"**Interaction {idx+1}:**")
                st.markdown(f"- **Time:** {interaction['time']}")
                st.markdown(f"- **Question:** {interaction['question']}")
                st.markdown(f"- **Response:** {interaction['response']}")

            # Add a button to switch to this past conversation
            if st.sidebar.button(f"Switch to Conversation {conv_idx+1}", key=f"switch_{conv_idx}"):
                # Save the current history to past conversations
                if st.session_state.current_conversation_index == -1 and st.session_state.history:
                    st.session_state.past_conversations.append(st.session_state.history)
                
                # Load the selected conversation into the current history
                st.session_state.history = conversation
                st.session_state.current_conversation_index = conv_idx
                st.sidebar.success(f"Switched to Conversation {conv_idx+1}")
                st.rerun()  # Refresh the app to reflect the changes

else:
    st.sidebar.write("No past conversations yet.")

# Add the "Start New Chat" button to reset only the current interaction history
if st.sidebar.button("Start a New Chat"):
    if st.session_state.history:
        # Save the current history to past conversations
        if st.session_state.current_conversation_index == -1:
            st.session_state.past_conversations.append(st.session_state.history)
        else:
            # Update the active conversation in past conversations
            st.session_state.past_conversations[st.session_state.current_conversation_index] = st.session_state.history

    # Clear the current history for a new chat session
    st.session_state.history = []
    st.session_state.current_conversation_index = -1
    st.session_state['content'] = ''
    st.session_state['generated_summary'] = ''
    st.sidebar.success("New chat started!")
    st.rerun()  # Refresh the app to reflect the changes

# Add functionality to save the entire conversation
def append_to_history(question, response):
    """Append a question and response to the current conversation history."""
    st.session_state.history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "response": response
    })


# Function to ask a question about the content
def ask_question(question):
    if question and selected_model_id:
        # Track start time for question response
        start_time = time.time()

        # Prepare the request payload for the question
        url = f"{base_url}/chat/completions"
        data = {
            "model": selected_model_id,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Use the following content to answer the user's questions."},
                {"role": "system", "content": st.session_state['content']},  # Use the current content as context
                {"role": "user", "content": question}
            ],
            "temperature": 0.7,
            "max_tokens": 200,
            "top_p": 0.9
        }

        try:
            # Send request to the API
            response = requests.post(url, headers=headers, json=data)
            
            # Track end time for question response
            end_time = time.time()
            response_time = end_time - start_time

            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']

                # Track the interaction history
                malaysia_tz = pytz.timezone("Asia/Kuala_Lumpur")
                current_time = datetime.now(malaysia_tz).strftime("%Y-%m-%d %H:%M:%S")

                # Only store interactions with a valid question and response
                if answer and question:
                    interaction = {
                        "time": current_time,
                        "question": question,
                        "response": answer,
                        "content_preview": st.session_state['content'][:100] if st.session_state['content'] else "No content available",
                        "response_time": f"{response_time:.2f} seconds"  # Store the response time
                    }
                    if "history" not in st.session_state:
                        st.session_state.history = []
                    st.session_state.history.append(interaction)  # Add a new entry only when there's a valid response

                    # Display the answer along with the response time
                    st.write(f"Answer: {answer}")
                    st.write(f"Question Response Time: {response_time:.2f} seconds")

                    # Update content with the latest answer
                    st.session_state['content'] += f"\n{question}: {answer}"

            else:
                st.write(f"Error {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            st.write(f"An error occurred: {e}")
