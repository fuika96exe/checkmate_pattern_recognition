const FULLWIDTH_DIGITS: Record<string, string> = {
  '０': '0',
  '１': '1',
  '２': '2',
  '３': '3',
  '４': '4',
  '５': '5',
  '６': '6',
  '７': '7',
  '８': '8',
  '９': '9',
};

const CHAR_REPLACEMENTS: Record<string, string> = {
  '俥': '车',
  '車': '车',
  '傌': '马',
  '馬': '马',
  '砲': '炮',
  '帥': '帅',
  '將': '将',
  '進': '进',
  '上': '进',
  '下': '退',
};

export const RESULT_REGEX =
  /^(1-0|0-1|1\/2-1\/2|0\.5-0\.5|\*|红胜|黑胜|和棋|黑方胜|红方胜|红先胜|黑先胜|红负|黑负|先胜|先负|先和|后胜|后负|后和)$/i;

export function normalizeFullwidth(text: string): string {
  let res = text.replace(/[０-９]/g, (ch) => FULLWIDTH_DIGITS[ch] || ch);
  res = res.replace(/　/g, ' ');
  return res;
}

export function normalizeMoveChars(text: string): string {
  return text.replace(/[俥車傌馬砲帥將進上下]/g, (ch) => CHAR_REPLACEMENTS[ch] || ch);
}

export function stripComments(text: string): string {
  // Preserve PlayOK block markers if present
  let safeText = text.replace(/START\{/g, '__PLAYOK_START__').replace(/\}END/g, '__PLAYOK_END__');
  // Remove { ... } multiline comments
  safeText = safeText.replace(/\{[\s\S]*?\}/g, ' ');
  // Remove comments inside （ ... ） if they are text descriptions
  safeText = safeText.replace(/（[^）]*[\u4e00-\u9fa5]{2,}[^）]*）/g, ' ');
  // Restore PlayOK block markers
  safeText = safeText.replace(/__PLAYOK_START__/g, 'START{').replace(/__PLAYOK_END__/g, '}END');
  return safeText;
}

export function isResultToken(token: string): boolean {
  return RESULT_REGEX.test(token.trim());
}

export function isJunkLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) return true;
  if (
    trimmed.startsWith('来源网站') ||
    trimmed.startsWith('棋谱由') ||
    trimmed.includes('www.dpxq.com') ||
    trimmed.includes('gdchess.com') ||
    trimmed.includes('xqbase.com') ||
    trimmed.includes('象棋百科') ||
    trimmed.includes('欢迎访问') ||
    trimmed.includes('推荐用象棋')
  ) {
    return true;
  }
  return false;
}
