# Automated Movie Review System

A conversation-based movie review chatbot that gathers information from multiple review sources to generate movie summaries, analyze different viewpoints, and provide an overall rating.

## Project Overview

The Automated Movie Review System is designed to give users a more complete understanding of a movie by combining information from multiple publicly accessible sources. Instead of relying on a single review or opinion, the chatbot retrieves relevant critic and audience perspectives, identifies areas of agreement and disagreement, and generates a source-supported response.

Users provide a movie title, and the system returns:
- A summary of the movie
- An analysis of the movie
- A comparison of critic and audience viewpoints
- An overall rating
- Links and references to the sources used

The chatbot is intended to respond to movie-title requests.

## Problem

Finding useful movie reviews across multiple websites can be time-consuming. Reviewers may also disagree, and a summary that ignores those differences can give users an incomplete picture of a film.

This project addresses that problem by retrieving relevant reviews and movie information from multiple sources and combining those perspectives into one response. The chatbot will distinguish factual information about a movie from subjective reviewer opinions and will make disagreements between sources clear.

## Data Sources

The expected sources include:

- [IMDb](https://www.imdb.com/)
- [Rotten Tomatoes](https://www.rottentomatoes.com/)
- [Wikipedia](https://www.wikipedia.org/)
- [Letterboxd](https://letterboxd.com/)

The project aims to use permitted public pages or equivalent authorized records, depending on source availability and reuse terms.

### Data Collection and Organization

Before collecting material, the project will review each source's terms of use, `robots.txt` rules, and permitted access methods.

- Use an authorized API or open dataset when crawling is not permitted.
- Do not bypass access controls.
- Record each collected item's source URL and collection date.
- Remove duplicate or irrelevant page text.
- Organize collected reviews and metadata for retrieval.
- Include critic and audience perspectives when available.

The goal is to maintain a collection of movie reviews and metadata that can be retrieved dynamically rather than relying only on a static knowledge base.

## System Workflow

The planned system follows this workflow:

1. **User Input:** The user enters a movie title.
2. **Data Collection:** The system retrieves relevant movie information and reviews from available sources.
3. **Review Generation:** A language model uses the retrieved information to produce a summary, analysis, comparison of viewpoints, and overall rating.
4. **User Feedback:** The user can rate the response positively or negatively.
5. **Model Improvement:** Reviewed feedback examples may be used to improve future responses through Direct Preference Optimization (DPO).

The chatbot will also consider relevant conversation context, such as whether a requested movie belongs to a series. Responses will include source links. If the available evidence is insufficient or sources disagree, the chatbot should communicate that limitation rather than make unsupported claims.

## Feedback and Model Improvement

The project plans to use **Direct Preference Optimization (DPO)** as its primary learning method.

For the same question and context:
- A positively rated response that is supported by its sources may be selected as the preferred response.
- A weaker or negatively rated response may be selected as the rejected response.
- After enough preference pairs have been reviewed, a small open model will be fine-tuned with DPO.

The purpose is to make future responses more likely to follow preferred answer patterns while continuing to rely on retrieved evidence.

A positive user rating does not automatically mean an answer is factually correct. Before examples are used for training, the team will review the supporting sources and preference pairs. The review process will look for issues such as confident but unsupported claims, excessive agreement, and failure to acknowledge disagreement among reviewers.

The system plans to log questions, sources, answers, and feedback without retaining personal identifiers.

## Evaluation

The project will prepare a held-out benchmark of at least **40 realistic movie questions** with verified answers and source links.

The initial system and the system after DPO will be compared using the same questions and retrieval setup.

The evaluation will measure:

- **Answer Quality:** The share of responses judged correct, relevant, and consistent with their sources.
- **Citation Correctness:** The share of cited pages that support the claims made.
- **Appropriate Abstention:** The share of unanswerable or unsupported questions for which the chatbot acknowledges the evidence gap.
- **Preference Win Rate:** The share of paired responses preferred by reviewers who do not know which version produced them.
- **Learning from Mistakes:** Before-and-after results, including at least three examples of initially weak or incorrect answers that improved after feedback.

The team will report the evaluation rubric, sample sizes, and results for both system versions. Failures will also be tracked to ensure that improvements in user preference do not come at the expense of factual accuracy or citation quality.

## Team

### Derrick Crawley — Undergraduate
- Co-lead source discovery and permission review.
- Build the data collection, cleaning, and retrieval pipeline.
- Develop the user interface and feedback capture.
- Help prepare the benchmark and analyze evaluation results.

### Parker Shanklin — Graduate
- Co-lead source discovery and corpus review.
- Build the response-generation and DPO workflow.
- Design checks for training preference pairs.
- Lead the related work and feedback design justification.

### Shared Responsibilities
Both team members will:
- Create the evaluation rubric.
- Verify answers and citations.
- Review failure cases.
- Document limitations.
- Write the project report.
- Demonstrate the system.

## Limitations and Responsible Use

- Movie reviews are subjective and may not reflect every viewer's opinion.
- Reviews and movie metadata may become outdated.
- Access and reuse permissions vary between sources.
- The chatbot will provide links to original sources and preserve source information.
- Conflicting reviewer opinions will be presented rather than hidden.
- Factual information about a movie will be distinguished from subjective reviewer opinions.
- The system will not collect personal information from chatbot users.

## Project Status

This repository documents the proposed system and its planned workflow. Implementation details, dependencies, installation instructions, and usage examples can be added as the software is developed.

---
