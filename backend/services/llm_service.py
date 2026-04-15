from langchain_groq import ChatGroq
from fastapi import HTTPException
from config import settings

def get_llm():
    ''' creating the groq llm and return it so it can be used 
    wherever required '''

    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Missing GROQ_API_KEY in environment.")

    return ChatGroq(
        api_key=settings.GROQ_API_KEY ,
        model = settings.GROQ_MODEL ,
        temperature=0 ,
    )

def generate_sql_from_prompt(prompt : str) ->str :
    ''' make sql query from a prepared prompt'''
    llm = get_llm()
    response = llm.invoke(prompt)

    # drag out only the content part 
    sql_text = getattr(response, "content", str(response)).strip()

    # remove the markdown
    if sql_text.startswith("```"):
        sql_text = sql_text.replace("```sql", "").replace("```", "").strip()

    return sql_text
