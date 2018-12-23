use crate::api::*;
use rand::Rng;

pub struct RandomDrafter {
}

impl Drafter for RandomDrafter {
    fn pick(&self, pack: &Vec<Card>, cards_owned: &Vec<Card>, draft_info: &DraftInfo) -> u32 {
        return rand::thread_rng().gen_range(0, pack.len() as u32);
    }
}