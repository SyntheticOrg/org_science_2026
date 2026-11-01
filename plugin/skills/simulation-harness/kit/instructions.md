# Instructions for the toy reporting game

Every `## name` section is loaded verbatim by `load_sections` and filled with `fill`. Replace these sections with the human instructions of the source study, keeping neutral labels and adding no strategic advice. Placeholders are in braces.

## system
You are taking part in a decision-making study as player {role}. Read the instructions carefully and answer every question in the requested format. Your earnings depend on the decisions made in the study.

## opening
There are two players, A and D, and {rounds} rounds. In each round the computer draws a number from 1 to 5. Player A sees the number; player D does not. {communication} Then player D chooses a number from 1 to 5.

Player D earns 10 points if the chosen number equals the drawn number, and 0 otherwise. {incentive}

## comm_report
Before D chooses, player A reports a number to D. The report can be true or not.

## comm_chat
Before D chooses, A and D can exchange messages for up to {turns} turns. Either player may stay silent; the conversation ends after a turn in which nobody writes.

## incentive_aligned
Player A earns 10 points if D chooses the drawn number, and 0 otherwise.

## incentive_conflict
Player A earns 10 points if D chooses the drawn number plus one (or 5 when the drawn number is 5), and 0 otherwise.

## round_a
Round {round}. The number this round is {state}.

## round_d
Round {round}. The computer has drawn a number.

## ask_report
Which number do you report to player D?

## ask_chat
Turn {turn} of {turns}. Conversation so far:
{transcript}
Write your message, or null to stay silent.

## ask_choice
{context}
Which number do you choose?

## note
Before your answer, write a short private note on your reasons. Nobody else sees it.

## result
Result of round {round}: the drawn number was {state}; D chose {choice}. A earned {pay_a} points and D earned {pay_d} points.
