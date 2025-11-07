# Populate Dummy Data for Campaigns

This management command populates dummy data for:
- **Property Visit/Call Scheduled** (goals)
- **AI Agent Follow-ups** (conversations)

## Usage

```bash
cd backend
source .venv/bin/activate  # or activate your virtual environment
python manage.py populate_dummy_data
```

## Options

- `--campaign-id ID`: Populate data for a specific campaign (default: uses first campaign)
- `--goals-count N`: Number of goals to create (default: 5)
- `--conversations-count N`: Number of conversations to create (default: 8)

## Examples

```bash
# Populate default amounts for first campaign
python manage.py populate_dummy_data

# Populate for specific campaign
python manage.py populate_dummy_data --campaign-id 1

# Create more goals and conversations
python manage.py populate_dummy_data --goals-count 10 --conversations-count 15
```

## What It Creates

### Goals (Property Visit/Call Scheduled)
- Creates scheduled visits/calls for random leads
- Sets realistic future dates (1-4 weeks ahead)
- Includes conversation summaries
- Mix of "visit" and "call" types

### Conversations (AI Agent Follow-ups)
- Creates realistic customer messages
- Generates appropriate AI agent responses
- Includes various intents (questions, inquiries, scheduling)
- Sets timestamps from past 1-14 days

## Requirements

- At least one campaign must exist
- Campaign must have leads associated with it
- Run `python manage.py load_leads` first if you need sample leads

