<?php

namespace App\Controller;

use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

class CardController extends AbstractController
{
    #[Route('/cards', name: 'card_index')]
    public function index(): Response
    {
        return $this->render('card/index.html.twig', [
            'cards' => [
                ['id' => 1, 'title' => 'Alpha', 'cover' => '/img/alpha.jpg'],
                ['id' => 2, 'title' => 'Beta', 'cover' => '/img/beta.jpg'],
            ],
        ]);
    }

    #[Route('/cards/{id}', name: 'card_detail')]
    public function detail(int $id): Response
    {
        return $this->render('card/detail.html.twig', [
            'card' => ['id' => $id, 'title' => 'Alpha', 'description' => 'A sample card.'],
        ]);
    }

    public function emailReceipt(int $cardId): void
    {
        // TODO send the download receipt email (T6)
    }

    public function unusedExportHelper(): string
    {
        return 'export-helper';
    }
}
