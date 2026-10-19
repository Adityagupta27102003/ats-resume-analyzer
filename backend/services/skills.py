"""Curated hard-skill vocabulary: canonical name -> aliases (all matched case-insensitively).

Used for (1) local skill extraction when Groq is unavailable and (2) normalising
LLM-extracted skills so "JS" in a resume matches "JavaScript" in a JD.
"""

SKILLS: dict[str, list[str]] = {
    # languages
    "Python": [], "Java": [], "JavaScript": ["js", "es6"], "TypeScript": ["ts"],
    "C": [], "C++": ["cpp"], "C#": ["csharp", "c sharp"], "Go": ["golang"], "Rust": [],
    "Kotlin": [], "Swift": [], "Ruby": [], "PHP": [], "Scala": [], "R": [], "Dart": [],
    "SQL": [], "Bash": ["shell scripting", "shell"], "MATLAB": [],
    # frontend
    "React": ["react.js", "reactjs"], "Next.js": ["nextjs"], "Angular": ["angularjs"],
    "Vue": ["vue.js", "vuejs"], "Svelte": [], "Redux": [], "HTML": ["html5"], "CSS": ["css3"],
    "Tailwind CSS": ["tailwind", "tailwindcss"], "Bootstrap": [], "Sass": ["scss"],
    "Vite": [], "Webpack": [], "jQuery": [],
    # backend
    "Node.js": ["node", "nodejs"], "Express": ["express.js", "expressjs"], "NestJS": [],
    "Django": [], "Flask": [], "FastAPI": [], "Spring Boot": ["spring"], "Hibernate": [],
    ".NET": ["dotnet", "asp.net"], "Ruby on Rails": ["rails"], "Laravel": [],
    "REST": ["rest api", "rest apis", "restful", "restful apis"], "GraphQL": [], "gRPC": [],
    "WebSockets": ["websocket"], "Microservices": ["microservice"],
    # data stores
    "PostgreSQL": ["postgres"], "MySQL": [], "SQLite": [], "MongoDB": ["mongo"],
    "Redis": [], "Cassandra": [], "DynamoDB": [], "Elasticsearch": [], "Firebase": [],
    "Supabase": [], "Oracle": [], "SQL Server": ["mssql"], "Snowflake": [], "BigQuery": [],
    # cloud / devops
    "AWS": ["amazon web services"], "Azure": [], "GCP": ["google cloud", "google cloud platform"],
    "Docker": [], "Kubernetes": ["k8s"], "Terraform": [], "Ansible": [], "Jenkins": [],
    "GitHub Actions": [], "CI/CD": ["ci cd", "continuous integration"], "Linux": [],
    "Nginx": [], "Git": [], "Kafka": ["apache kafka"], "RabbitMQ": [], "Celery": [],
    "Lambda": ["aws lambda"], "EC2": [], "S3": [], "Vercel": [], "Heroku": [],
    # ML / data
    "Machine Learning": ["ml"], "Deep Learning": ["dl"], "NLP": ["natural language processing"],
    "Computer Vision": ["cv"], "TensorFlow": [], "PyTorch": ["torch"], "Keras": [],
    "scikit-learn": ["sklearn", "scikit learn"], "Pandas": [], "NumPy": [], "SciPy": [],
    "Matplotlib": [], "Seaborn": [], "spaCy": [], "NLTK": [], "Hugging Face": ["huggingface", "transformers"],
    "BERT": [], "LLM": ["llms", "large language models"], "LangChain": [], "RAG": [],
    "OpenCV": [], "XGBoost": [], "Spark": ["pyspark", "apache spark"], "Hadoop": [],
    "Airflow": ["apache airflow"], "Tableau": [], "Power BI": ["powerbi"], "Excel": [],
    "Data Analysis": [], "Statistics": [], "MLOps": [], "MLflow": [],
    # testing / practices
    "Pytest": [], "Jest": [], "JUnit": [], "Selenium": [], "Cypress": [], "Playwright": [],
    "Unit Testing": ["unit tests"], "TDD": ["test driven development"],
    "Agile": ["scrum"], "System Design": [], "Data Structures": ["dsa"], "Algorithms": [],
    "OOP": ["object oriented programming", "object-oriented programming"],
    "Design Patterns": [], "Distributed Systems": [], "Multithreading": ["concurrency"],
    # mobile
    "Android": [], "iOS": [], "React Native": [], "Flutter": [],
    # security / misc
    "OAuth": ["oauth2"], "JWT": [], "Authentication": ["auth"], "Figma": [], "Jira": [],
    "Postman": [], "Streamlit": [],
}

# Very short aliases cause false positives in free text ("ts", "ml", "cv", "auth"
# appear in unrelated words/contexts), so they are only trusted as exact skill-list
# entries, never matched inside prose.
AMBIGUOUS_ALIASES = {"js", "ts", "ml", "dl", "cv", "auth", "shell", "spring", "node", "mongo",
                     "torch", "transformers", "r", "c", "go", "dsa", "rails", "scrum"}

ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in SKILLS.items():
    ALIAS_TO_CANONICAL[_canonical.lower()] = _canonical
    for _alias in _aliases:
        ALIAS_TO_CANONICAL[_alias.lower()] = _canonical


def canonicalize(skill: str) -> str:
    """Map a raw skill string to its canonical name, or return it cleaned up."""
    key = skill.strip().lower()
    return ALIAS_TO_CANONICAL.get(key, skill.strip())


# Strong action verbs for resume bullets (past + present tense).
ACTION_VERBS = {
    "achieved", "accelerated", "analyzed", "architected", "automated", "built", "collaborated",
    "configured", "created", "debugged", "delivered", "deployed", "designed", "developed",
    "drove", "engineered", "enhanced", "established", "executed", "implemented", "improved",
    "increased", "integrated", "introduced", "launched", "led", "maintained", "managed",
    "mentored", "migrated", "modernized", "monitored", "optimized", "orchestrated", "owned",
    "pioneered", "programmed", "published", "reduced", "refactored", "resolved", "scaled",
    "shipped", "simplified", "spearheaded", "streamlined", "tested", "trained", "transformed",
    "upgraded", "wrote", "boosted", "cut", "decreased", "deployed", "devised", "documented",
    "evaluated", "extracted", "fine-tuned", "formulated", "generated", "identified", "initiated",
    "investigated", "modeled", "organized", "partnered", "planned", "presented", "prototyped",
    "researched", "restructured", "revamped", "secured", "solved", "standardized", "supported",
    "translated", "visualized", "won",
    "build", "design", "develop", "implement", "lead", "manage", "optimize", "create", "deploy",
}

WEAK_PHRASES = [
    "responsible for", "worked on", "helped with", "helped to", "duties included",
    "assisted in", "assisted with", "involved in", "participated in", "tasked with",
]
