from django.core.management.base import BaseCommand
from drafts.models import Draft, Drafter


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

        print('About to delete {} drafts: {}'.format(len(drafts_to_delete), drafts_to_delete))
        if options['dry_run']:
            print('--dry-run specified; nothing deleted')
        else:
            deletions = drafts_to_delete.delete()
            print('Deletions: {}'.format(deletions))
