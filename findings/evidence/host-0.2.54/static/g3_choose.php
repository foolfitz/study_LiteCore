<?php
// SPEC-P-demo-batch-6 G3: the spreadsheet BlankDocument chooses is the document's triple as .ods, it is in blank-ods' manifest, and choose() is unchanged.
require $argv[1];
use OCA\LiteCore\Template\BlankDocument as B;
$languages = ['en', 'en_GB', 'de', 'fr', 'es', 'es_MX', 'it', 'nl', 'pt_BR', 'pt_PT', 'zh_TW', 'zh_HK', 'zh_CN', 'ja', 'ko', 'ru', 'ar'];
$locales = [null, 'en_US', 'de_DE', 'zh_TW', 'es_MX', 'ja_JP'];
$manifest = B::manifest(B::DIR_ODS)['files'];
$rows = []; $bad = [];
foreach ($languages as $l) { foreach ($locales as $loc) {
  $d = B::choose($l, $loc); $s = B::chooseSpreadsheet($l, $loc);
  $same = substr($d['file'], 0, -4) === substr($s['file'], 0, -4) && str_ends_with($s['file'], '.ods');
  $known = isset($manifest[$s['file']]);
  $readable = strlen(B::read($s['file'], B::DIR_ODS)) > 0;
  if (!$same || !$known || !$readable) $bad[] = [$l, $loc, $d['file'], $s['file']];
  $rows[] = [$l, $loc, $s['file']];
} }
echo json_encode(['pairs' => count($rows), 'distinctFiles' => count(array_unique(array_column($rows, 2))), 'bad' => $bad, 'verdict' => $bad ? 'G3_RED' : 'G3_HOLDS'], JSON_PRETTY_PRINT);
exit($bad ? 1 : 0);
