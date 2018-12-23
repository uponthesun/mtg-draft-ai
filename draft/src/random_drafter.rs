use crate::api;
use rand::Rng;

pub struct RandomDrafter {
}

impl api::Drafter for RandomDrafter {
    fn pick(&self, pack: &Vec<api::Card>, cards_owned: &Vec<api::Card>) -> u32 {
        return rand::thread_rng().gen_range(0, pack.len() as u32);
    }
}