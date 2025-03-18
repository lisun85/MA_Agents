# FamilyOfficeFinder Crew

Welcome to the FamilyOfficeFinder Crew project, powered by [crewAI](https://crewai.com). This template is designed to help you set up a multi-agent AI system with ease, leveraging the powerful and flexible framework provided by crewAI. Our goal is to enable your agents to collaborate effectively on complex tasks, maximizing their collective intelligence and capabilities.

## Installation

Ensure you have Python >=3.10 <3.13 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:

```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```
### Customizing

**Add your `OPENAI_API_KEY` into the `.env` file**

- Modify `src/family_office_finder/config/agents.yaml` to define your agents
- Modify `src/family_office_finder/config/tasks.yaml` to define your tasks
- Modify `src/family_office_finder/crew.py` to add your own logic, tools and specific args
- Modify `src/family_office_finder/main.py` to add custom inputs for your agents and tasks

## Running the Project

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

```bash
$ crewai run
```

This command initializes the family_office_finder Crew, assembling the agents and assigning them tasks as defined in your configuration.

This example, unmodified, will run the create a `report.md` file with the output of a research on LLMs in the root folder.

## Understanding Your Crew

The family_office_finder Crew is composed of multiple AI agents, each with unique roles, goals, and tools. These agents collaborate on a series of tasks, defined in `config/tasks.yaml`, leveraging their collective skills to achieve complex objectives. The `config/agents.yaml` file outlines the capabilities and configurations of each agent in your crew.

## Support

For support, questions, or feedback regarding the FamilyOfficeFinder Crew or crewAI.
- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.

# Website Scraper

A simple tool to scrape websites and save their content locally.

## Setup

1. Make sure you have Python 3.10+ installed
2. Install the required packages:
   ```
   pip install playwright dotenv
   ```
3. Install Playwright browsers:
   ```
   playwright install
   ```

## Usage

1. Create a text file with URLs to scrape (one per line)
2. Run the scraper:
   ```
   python -m family_office_finder.scrape_urls --file urls_to_scrape.txt
   ```

### Options

- `--file` or `-f`: Path to file containing URLs to scrape (required)
- `--depth` or `-d`: Maximum link depth to follow (default: 2)
- `--pages` or `-p`: Maximum number of pages to crawl per site (default: 10)
- `--time` or `-t`: Maximum time in minutes to spend per site (default: 5)

## Output

All scraped content is saved to:
`~/Documents/Github/MA_Agents/family_office_finder/output`

For each website, a timestamped directory is created containing:
- JSON files with full page data
- TXT files with readable text content
- A crawl_summary.json file with metadata about the crawl

A global scrape_summary.json file is also created with information about all scraped sites.
