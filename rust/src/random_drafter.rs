use crate::api::*;
use rand::Rng;

pub struct RandomDrafter {
}

impl Drafter for RandomDrafter {
    fn pick<'a>(&self, pack: &'a [Card], cards_owned: &[Card], draft_info: &DraftInfo) -> &'a Card {
        let index = rand::thread_rng().gen_range(0, pack.len());
        &pack[index]
    }
}