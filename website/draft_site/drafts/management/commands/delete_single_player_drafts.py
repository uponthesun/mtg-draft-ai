from django.core.management.base import BaseCommand
from drafts.models import Draft, Drafter


DELETE_BATCH_SIZE = 100


class Command(BaseCommand):
    help = 'Deletes drafts that only have one human player'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Prints out drafts to delete but does not actually delete them',
        )

    def handle(self, *args, **options):
        all_drafts = Draft.objects.all()

        human_drafters_by_draft_id = {}
        for drafter in Drafter.objects.filter(bot=False):
            human_drafters_by_draft_id.setdefault(drafter.draft_id, [])
            human_drafters_by_draft_id[drafter.draft_id].append(drafter)

        single_player_drafts = [draft for draft in all_drafts if len(human_drafters_by_draft_id[draft.id]) <= 1]

        drafts_to_delete = Draft.objects.filter(id__in=[draft.id for draft in single_player_drafts])
        draft_ids_to_delete = [draft.id for draft in drafts_to_delete]

        print('About to delete {} drafts: {}'.format(len(drafts_to_delete), draft_ids_to_delete))
        for i in range(0, len(draft_ids_to_delete), DELETE_BATCH_SIZE):
            batch = draft_ids_to_delete[i:i + DELETE_BATCH_SIZE]
            if options['dry_run']:
                print('--dry-run specified; nothing deleted, would have deleted: {}'.format(batch))
            else:
                deletions = Draft.objects.filter(id__in=batch).delete()
                print('Deletions: {}'.format(deletions))
