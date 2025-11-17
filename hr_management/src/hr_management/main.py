from crew import hr_crew, memory


def main():
    print("=== HR Automation Orchestrator ===")

    # Resume Screening
    pdf_path = input("Enter path to resume PDF: ")
    job_role = input("Enter desired job role: ")
    fields, score = hr_crew.tasks[0].run(pdf_path, job_role)
    print("\nResume Screening Result:")
    print(fields)
    print(f"Score: {score}")

    # Onboarding Plan
    plan = hr_crew.tasks[1].run(fields, score, job_role)
    print("\nOnboarding Plan:")
    print(plan)

    # Policy Q&A
    questions = []
    print("\nEnter policy questions (type 'done' to finish):")
    while True:
        q = input("Question: ")
        if q.lower() == "done":
            break
        questions.append(q)
    answers = hr_crew.tasks[2].run(questions)
    print("\nPolicy Q&A Answers:")
    for q, a in zip(questions, answers):
        print(f"Q: {q}\nA: {a}\n")

    print("\nMemory System State:")
    print(memory.data)


if __name__ == "__main__":
    main()